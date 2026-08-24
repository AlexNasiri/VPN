#!/bin/sh
set -e

# Railway (and most volume-backed platforms) mount persistent Volumes at
# container start time with root:root ownership, which overrides whatever
# chown was baked into the image at build time. Since this container runs
# the app as a non-root user for security, we need to re-fix ownership on
# every start, before dropping privileges — otherwise sqlite can't open its
# database file on a freshly mounted /data.
#
# This script always runs as root (see Dockerfile: no USER before
# ENTRYPOINT), so it can safely chown /data no matter who mounted it or
# what its previous ownership was, then hands off execution to the
# unprivileged "vortex" user via gosu.

mkdir -p /data
chown -R vortex:vortex /data

exec gosu vortex "$@"
