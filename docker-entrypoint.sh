#!/bin/sh
# Render config.yaml from the secret-free template plus environment variables,
# into tmpfs so credentials never land in an image layer or the container's
# writable layer. /app/config.yaml is a symlink to /dev/shm/config.yaml (see
# the Dockerfile).
set -eu

# Required.
: "${MATTERBOT_TOKEN:?MATTERBOT_TOKEN is required (the bot account password or a personal access token)}"
: "${MATTERMOST_HOST:?MATTERMOST_HOST is required (hostname of your Mattermost server)}"
: "${MATTERBOT_USERNAME:?MATTERBOT_USERNAME is required (the bot account username)}"
: "${MATTERMOST_TEAM:?MATTERMOST_TEAM is required (the team name, as it appears in the URL)}"

# Optional, with defaults.
: "${MATTERMOST_PORT:=443}"
: "${MATTERMOST_SCHEME:=https}"
: "${MATTERBOT_ADMIN_ID:=}"
: "${AI_ENABLED:=False}"
: "${AI_BASE_URL:=http://localhost:11434/v1}"
: "${AI_MODEL:=}"
: "${AI_API_KEY:=}"

case "$AI_ENABLED" in
    True|true|TRUE) : "${AI_MODEL:?AI_MODEL is required when AI_ENABLED is true}" ;;
    False|false|FALSE) ;;
    *) echo "AI_ENABLED must be True or False, got: $AI_ENABLED" >&2; exit 1 ;;
esac

export MATTERBOT_TOKEN MATTERMOST_HOST MATTERBOT_USERNAME MATTERMOST_TEAM \
       MATTERMOST_PORT MATTERMOST_SCHEME MATTERBOT_ADMIN_ID \
       AI_ENABLED AI_BASE_URL AI_MODEL AI_API_KEY

umask 077
# Name the variables: a bare envsubst would also eat any other $ in the config.
envsubst '${MATTERBOT_TOKEN} ${MATTERMOST_HOST} ${MATTERBOT_USERNAME}
          ${MATTERMOST_TEAM} ${MATTERMOST_PORT} ${MATTERMOST_SCHEME}
          ${MATTERBOT_ADMIN_ID} ${AI_ENABLED} ${AI_BASE_URL} ${AI_MODEL}
          ${AI_API_KEY}' \
    < "$(dirname "$0")/config.container.yaml" \
    > "${MATTERBOT_CONFIG_OUT:-/dev/shm/config.yaml}"

exec "$@"
