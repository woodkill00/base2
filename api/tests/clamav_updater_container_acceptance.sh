#!/bin/sh
set -eu

readonly image='clamav/clamav@sha256:1fdfd24c6f0a0fb60788481487459a6d4eda8a9b448641594e04db8410d34422'
readonly container='base2-clamav-updater-acceptance'
readonly volume='base2-clamav-updater-acceptance-db'
readonly evidence_timeout_seconds=120
readonly evidence_safety_margin_seconds=6
readonly command_timeout_seconds=30
readonly evidence_kill_grace_seconds=5
readonly cleanup_timeout_seconds=10
readonly cleanup_kill_grace_seconds=5
repo_root="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
# Reserve the five-second SIGKILL grace plus one second of clock/sleep
# granularity inside the public evidence ceiling.
evidence_deadline="$(( $(date -u +%s) + evidence_timeout_seconds - evidence_safety_margin_seconds ))"

cleanup() {
  timeout --foreground --kill-after="$cleanup_kill_grace_seconds" \
    "$cleanup_timeout_seconds" docker rm -f "$container" >/dev/null 2>&1 || true
  timeout --foreground --kill-after="$cleanup_kill_grace_seconds" \
    "$cleanup_timeout_seconds" docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

docker_call() {
  now_epoch="$(date -u +%s)"
  remaining_seconds="$((evidence_deadline - now_epoch))"
  if test "$remaining_seconds" -le 0; then
    echo 'updater acceptance exhausted its 120-second evidence budget' >&2
    return 124
  fi
  command_budget="$remaining_seconds"
  if test "$command_budget" -gt "$command_timeout_seconds"; then
    command_budget="$command_timeout_seconds"
  fi
  if timeout --foreground --kill-after="$evidence_kill_grace_seconds" \
    "$command_budget" docker "$@"; then
    command_status=0
  else
    command_status="$?"
  fi
  case "$command_status" in
    124|137)
      echo "bounded Docker operation timed out: docker $1" >&2
      ;;
  esac
  return "$command_status"
}

reject_timeout() {
  case "$1" in
    124|137)
      echo 'updater acceptance failed closed; bounded cleanup will now remove the exact container and volume' >&2
      exit "$1"
      ;;
  esac
}

cleanup
docker_call volume create "$volume" >/dev/null

start_updater() {
  checks="$1"
  docker_call run -d --name "$container" \
    --platform linux/amd64 \
    --network none \
    --user 100:101 \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --pids-limit 32 \
    --memory 512m \
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
set +e
definition_identity="$(docker_call exec --user 100:101 "$container" \
  clamscan --database=/var/lib/clamav --version)"
identity_status="$?"
set -e
reject_timeout "$identity_status"
test "$identity_status" -eq 0
definition_date="$(printf '%s\n' "$definition_identity" | cut -d/ -f3-)"
reference_epoch="$(( $(date -u -d "$definition_date" +%s) + 3600 ))"

run_health() {
  docker_call exec --user 100:101 "$container" \
    /bin/sh /usr/local/bin/base2-clamav-health --reference-epoch "$reference_epoch"
}

while :; do
  set +e
  run_health
  health_status="$?"
  set -e
  if test "$health_status" -eq 0; then
    break
  fi
  reject_timeout "$health_status"
  if test "$(docker_call inspect "$container" --format '{{.State.Running}}')" != true; then
    echo 'updater exited before becoming healthy' >&2
    docker_call logs "$container" >&2 || true
    exit 1
  fi
  sleep 1
done

set +e
definition_identity="$(docker_call exec --user 100:101 "$container" \
  clamscan --database=/var/lib/clamav --version)"
identity_status="$?"
set -e
reject_timeout "$identity_status"
test "$identity_status" -eq 0
definition_version="$(printf '%s\n' "$definition_identity" | cut -d/ -f2)"
now_epoch="$reference_epoch"
docker_call exec --user 100:101 "$container" /bin/sh -c \
  "printf '%s %s\\n' '$((definition_version - 1))' '$now_epoch' > /var/lib/clamav/.base2-updater-health"
run_health
test "$(docker_call exec --user 100:101 "$container" cut -d' ' -f1 \
  /var/lib/clamav/.base2-updater-health)" = "$definition_version"

# The health command must require updater-volume write authority.
if docker_call exec --user 65534:65534 "$container" /bin/sh /usr/local/bin/base2-clamav-health \
  --reference-epoch "$reference_epoch" \
  >/dev/null 2>&1; then
  echo 'health unexpectedly passed without updater-volume write authority' >&2
  exit 1
else
  reject_timeout "$?"
fi

# A signed but non-advancing database must not remain healthy indefinitely.
docker_call exec --user 100:101 "$container" /bin/sh -c \
  "printf '%s %s\\n' '$definition_version' '$((reference_epoch - 86401))' > /var/lib/clamav/.base2-updater-health"
if run_health; then
  echo 'health unexpectedly accepted a non-advancing definition set' >&2
  exit 1
else
  reject_timeout "$?"
fi
docker_call exec --user 100:101 "$container" rm -f /var/lib/clamav/.base2-updater-health
run_health

# An altered daemon configuration must fail even while freshclam is alive.
docker_call rm -f "$container" >/dev/null
start_updater 1
sleep 1
if run_health; then
  echo 'health unexpectedly accepted altered updater configuration' >&2
  exit 1
else
  reject_timeout "$?"
fi

# Process death cannot be hidden by definition files left on the volume.
docker_call kill --signal KILL "$container" >/dev/null
docker_call wait "$container" >/dev/null
if docker_call exec --user 100:101 "$container" /bin/sh /usr/local/bin/base2-clamav-health 2>/dev/null; then
  echo 'health unexpectedly passed after updater process death' >&2
  exit 1
else
  reject_timeout "$?"
fi

printf '%s\n' '{"fixedReferenceClock":true,"signedDefinitions":true,"foreground":true,"networkless":true,"status":"pass","writableVolume":true}'
