#!/bin/sh
set -eu

# Управляющие символы не допускаются в однострочном формате конфигурации.
if [ -z "${REDIS_PASSWORD:-}" ] || printf '%s' "$REDIS_PASSWORD" | LC_ALL=C grep -q '[[:cntrl:]]'; then
    exit 1
fi
escaped=$(printf '%s' "$REDIS_PASSWORD" | sed 's/\\/\\\\/g; s/"/\\"/g')
exec docker-entrypoint.sh redis-server - <<EOF
appendonly yes
maxmemory 256mb
maxmemory-policy allkeys-lru
requirepass "$escaped"
EOF
