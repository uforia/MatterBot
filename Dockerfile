FROM python:3.13-slim

# graphviz: attackmatrix graphs. pandoc: pypandoc. pango: weasyprint.
# build-essential covers any requirement that has no wheel for this platform.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential ca-certificates gettext-base graphviz pandoc \
      libpango-1.0-0 libpangoft2-1.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Private CA roots, if your Mattermost or AI endpoint uses a certificate signed by
# an internal CA. Drop the public *.crt files into ./ca before building; with none
# there, only the system trust store is used. (*.crt in ./ca is git-ignored.)
COPY ca/ /usr/local/share/ca-certificates/
RUN update-ca-certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# config.yaml names bindmap/feedmap/logfile as bare relative paths. Point them
# at the /data volume with symlinks so the config needs no container-specific
# edits and state survives a recreate. The targets do not exist until first write.
RUN useradd --uid 1000 --create-home app \
 && mkdir /data && chown app:app /data \
 && ln -s /data/bindmap.json /app/bindmap.json \
 && ln -s /data/feedmap.json /app/feedmap.json \
 && ln -s /data/matterfeed.log /app/matterfeed.log \
 && ln -s /dev/shm/config.yaml /app/config.yaml \
 && chmod +x /app/docker-entrypoint.sh
USER app

VOLUME /data
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-u", "matterbot.py"]
