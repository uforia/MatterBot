#!/usr/bin/env python3

# Every module must set the CHANNELS variable to indicate where information should be sent to in Mattermost
#
# Every module must implement the query() function.
# This query() function is called by the main worker and has only one parameter: the number of historic
# items that should be returned in the list.
#
# Every module must return a list [...] with 0, 1 ... n entries
# of 2-tuples: ('<channel>', '<content>')
#
# <channel>: basically the destination channel in Mattermost, e.g. 'Newsfeed', 'Incident', etc.
# <content>: the content of the message, MD format possible

import csv
import datetime
import paramiko
import re
import traceback
from io import StringIO
from pathlib import Path
try:
    from modules.thorparser import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/thorparser/settings.py').is_file():
        try:
            from modules.thorparser import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=settings.ENTRIES):
    items = []
    try:
        csvattachments = []
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(settings.SFTPSERVER['hostname'],username=settings.SFTPSERVER['username'],password=settings.SFTPSERVER['password'])
            sftp = client.open_sftp()
        except Exception as e:
            content = "An error occurred during the THOR parsing:\n"+str(traceback.format_exc())
            for channel in settings.CHANNELS:
                items.append([channel,content])
        if sftp:
            stripchars = '`\t\n\r\'\"\|'
            regex = re.compile('[%s]' % stripchars)
            sus_files = {}
            sftp.chdir(settings.SFTPSERVER['upload'])
            files=sftp.listdir()
            for file in files:
                if file.lower().endswith(settings.THOR['md5s']):
                    host = file.split('_')[0]
                    date = str(datetime.datetime.fromtimestamp(sftp.stat(file).st_mtime))
                    if not host in sus_files:
                        sus_files[host] = {
                            'date': date,
                            'sus_files': [],
                            'info_files': 0,
                        }
                    contents = sftp.open(file).read()
                    csv_data = csv.reader(StringIO(contents.decode('utf-8')),delimiter=',')
                    for row in csv_data:
                        md5,path,subscore = row
                        if int(subscore) >= settings.THOR['subscore_threshold']:
                            sus_files[host]['sus_files'].append({
                                'md5': md5,
                                'path': regex.sub(' => ',path),
                                'subscore': int(subscore),
                            })
                        else:
                            sus_files[host]['info_files'] += 1
                    try:
                        sftp.posix_rename(file,settings.SFTPSERVER['archive']+'/'+file)
                    except Exception as e:
                        content = "An error occurred archiving the CSV file: `%s`\n%s" % (file,str(traceback.format_exc()))
                        for channel in settings.CHANNELS:
                            items.append([channel,content])
            sftp.close()
            if len(sus_files):
                for host in sus_files:
                    content = '> **THOR APT Scanner Results** - **Hostname**: `%s` - **Timestamp**: `%s` - **Threshold**: `%s`\n' % (host,sus_files[host]['date'],settings.THOR['subscore_threshold'])
                    for channel in settings.CHANNELS:
                        items.append([channel,content])
                    content = '| **MD5** | **Path** | **Subscore** | **Severity** |'
                    content += '\n| :- | :- | -: | -: |'
                    for row in sorted(sus_files[host]['sus_files'], key=lambda x: x['subscore'], reverse=True):
                        md5 = row['md5']
                        path = row['path']
                        subscore = row['subscore']
                        if subscore >= settings.THOR['subscore_high']:
                            severity = 'High'
                        elif subscore >= settings.THOR['subscore_medium']:
                            severity = 'Medium'
                        elif subscore >= settings.THOR['subscore_low']:
                            severity = 'Low'
                        else:
                            severity = 'Info'
                        content += '\n| `%s` | `%s` | `%s` | `%s` |' % (md5,path,subscore,severity)
                    content += '\n\nNumber of \'low scoring\' (subscore below: **`%s`**) files: **`%s`**' % (settings.THOR['subscore_low'],sus_files[host]['info_files'])
                    for channel in settings.CHANNELS:
                        items.append([channel,content])
    except Exception as e:
        content = "An error occurred during the THOR parsing:\n"+str(traceback.format_exc())
        items.append([channel,content])
    finally:
        return items

if __name__ == "__main__":
    print(query())
