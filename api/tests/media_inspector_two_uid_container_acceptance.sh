#!/bin/sh
set -eu

readonly image="${MEDIA_INSPECTOR_TEST_IMAGE:-base2-media-inspector:two-uid}"
readonly volume=base2-media-inspector-two-uid-spool
readonly supervisor=base2-media-inspector-two-uid-supervisor
signing_key="$(python3 -c "import base64; print(base64.urlsafe_b64encode(b'k'*32).decode())")"

cleanup() {
  docker rm -f "$supervisor" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM
cleanup
docker volume create "$volume" >/dev/null

run_init() {
  docker run --rm --platform linux/amd64 --network none --user 0:0 --read-only \
    --cap-drop ALL --cap-add CHOWN --security-opt no-new-privileges \
    --pids-limit 8 --memory 32m --cpus 0.1 \
    --volume "$volume:/var/lib/base2/media-inspector" \
    --entrypoint /usr/bin/python "$image" /app/api/scripts/media_inspector_spool_init.py
}

run_producer() {
  docker run --rm --platform linux/amd64 --network none --user 1000:1000 --read-only \
    --cap-drop ALL --security-opt no-new-privileges --pids-limit 8 --memory 256m --cpus 0.25 \
    --volume "$volume:/var/lib/base2/media-inspector" \
    --entrypoint /usr/bin/python "$image" /app/api/tests/media_inspector_two_uid_producer.py "$@"
}

start_supervisor() {
  docker run -d --name "$supervisor" --platform linux/amd64 --network none --ipc private \
    --user 0:0 --group-add 1000 --read-only --cap-drop ALL \
    --cap-add SETUID --cap-add SETGID --cap-add SETPCAP \
    --security-opt no-new-privileges --pids-limit 16 --memory 1536m --cpus 0.75 \
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
    --volume "$volume:/var/lib/base2/media-inspector" \
    --env MEDIA_INSPECTOR_SIGNING_KEY="$signing_key" \
    --env MEDIA_INSPECTOR_BUILD_IDENTITY="base2-media-inspector:$(printf '%064d' 0)" \
    --env MEDIA_INSPECTOR_SPOOL_ROOT=/var/lib/base2/media-inspector \
    --env MEDIA_INSPECTOR_SPOOL_PRODUCER_UID=1000 \
    --env MEDIA_INSPECTOR_SPOOL_PRODUCER_GID=1000 \
    "$image" >/dev/null
  sleep 1
  test "$(docker inspect "$supervisor" --format '{{.State.Running}}')" = true
}

# Fresh conversion and exact desired-state replay must both succeed.
run_init
run_init
# Any third state must fail closed; restore it only as the unprivileged owner.
docker run --rm --platform linux/amd64 --network none --user 1000:1000 --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --volume "$volume:/var/lib/base2/media-inspector" \
  --entrypoint /usr/bin/python "$image" -c \
  "import os; os.chmod('/var/lib/base2/media-inspector',0o700)"
if run_init; then
  echo 'initializer accepted a non-contract state' >&2
  exit 1
fi
docker run --rm --platform linux/amd64 --network none --user 1000:1000 --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --volume "$volume:/var/lib/base2/media-inspector" \
  --entrypoint /usr/bin/python "$image" -c \
  "import os; os.chmod('/var/lib/base2/media-inspector',0o770)"

start_supervisor
run_producer
run_producer --verify-crowded-bound
test "$(docker inspect "$supervisor" --format '{{.State.Running}}')" = true
docker rm -f "$supervisor" >/dev/null

# Persist exact crash residue while the supervisor is down, then prove a new
# supervisor instance performs bounded recovery without client-side unlinking.
run_producer --stage-recovery
start_supervisor
run_producer --verify-recovery
test "$(docker inspect "$supervisor" --format '{{.State.Running}}')" = true
