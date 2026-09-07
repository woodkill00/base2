#!/bin/sh
set -eu

readonly image='clamav/clamav@sha256:1fdfd24c6f0a0fb60788481487459a6d4eda8a9b448641594e04db8410d34422'
readonly container='base2-clamav-updater-acceptance'
readonly volume='base2-clamav-updater-acceptance-db'
repo_root="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"

cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM
cleanup
docker volume create "$volume" >/dev/null

start_updater() {
  checks="$1"
  docker run -d --name "$container" \
    --platform linux/amd64 \
    --network none \
    --user 100:101 \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --pids-limit 32 \
    --memory 256m \
    --cpus 0.25 \
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=32m \
    --tmpfs /run:rw,nosuid,nodev,noexec,size=8m \
    --volume "$volume:/var/lib/clamav" \
    --volume "$repo_root/api/config/freshclam.conf:/etc/clamav/freshclam-base2.conf:ro" \
    --volume "$repo_root/api/scripts/clamav_updater_health.sh:/usr/local/bin/base2-clamav-health:ro" \
    --entrypoint /usr/bin/freshclam \
    "$image" \
    --daemon --foreground --stdout "--checks=$checks" --user=clamav \
    --config-file=/etc/clamav/freshclam-base2.conf >/dev/null
}

start_updater 24
attempt=0
until docker exec --user 100:101 "$container" /bin/sh /usr/local/bin/base2-clamav-health; do
  attempt="$((attempt + 1))"
  test "$attempt" -lt 10
  test "$(docker inspect "$container" --format '{{.State.Running}}')" = true
  sleep 1
done

definition_version="$(docker exec --user 100:101 "$container" \
  clamscan --database=/var/lib/clamav --version | cut -d/ -f2)"
now_epoch="$(date -u +%s)"
docker exec --user 100:101 "$container" /bin/sh -c \
  "printf '%s %s\\n' '$((definition_version - 1))' '$now_epoch' > /var/lib/clamav/.base2-updater-health"
docker exec --user 100:101 "$container" /bin/sh /usr/local/bin/base2-clamav-health
test "$(docker exec --user 100:101 "$container" cut -d' ' -f1 \
  /var/lib/clamav/.base2-updater-health)" = "$definition_version"

# The health command must require updater-volume write authority.
if docker exec --user 65534:65534 "$container" /bin/sh /usr/local/bin/base2-clamav-health \
  >/dev/null 2>&1; then
  echo 'health unexpectedly passed without updater-volume write authority' >&2
  exit 1
fi

# A signed but non-advancing database must not remain healthy indefinitely.
docker exec --user 100:101 "$container" /bin/sh -c \
  "printf '%s %s\\n' '$definition_version' '$((now_epoch - 86401))' > /var/lib/clamav/.base2-updater-health"
if docker exec --user 100:101 "$container" /bin/sh /usr/local/bin/base2-clamav-health; then
  echo 'health unexpectedly accepted a non-advancing definition set' >&2
  exit 1
fi
docker exec --user 100:101 "$container" rm -f /var/lib/clamav/.base2-updater-health
docker exec --user 100:101 "$container" /bin/sh /usr/local/bin/base2-clamav-health

# An altered daemon configuration must fail even while freshclam is alive.
docker rm -f "$container" >/dev/null
start_updater 1
sleep 1
if docker exec --user 100:101 "$container" /bin/sh /usr/local/bin/base2-clamav-health; then
  echo 'health unexpectedly accepted altered updater configuration' >&2
  exit 1
fi

# Process death cannot be hidden by definition files left on the volume.
docker kill --signal KILL "$container" >/dev/null
docker wait "$container" >/dev/null
if docker exec --user 100:101 "$container" /bin/sh /usr/local/bin/base2-clamav-health 2>/dev/null; then
  echo 'health unexpectedly passed after updater process death' >&2
  exit 1
fi

printf '%s\n' '{"signedDefinitions":true,"foreground":true,"networkless":true,"status":"pass","writableVolume":true}'
