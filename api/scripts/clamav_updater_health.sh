#!/bin/sh
set -eu

readonly database_root=/var/lib/clamav
readonly state_file="$database_root/.base2-updater-health"
readonly maximum_age_seconds=86400

case "$#:${1-}" in
  0:)
    now_epoch="$(date -u +%s)"
    ;;
  2:--reference-epoch)
    case "$2" in ''|*[!0-9]*) exit 64 ;; esac
    now_epoch="$2"
    ;;
  *) exit 64 ;;
esac

test "$(cat /proc/1/comm)" = freshclam
kill -0 1
command_line="$(tr '\000' ' ' </proc/1/cmdline)"
case "$command_line" in
  *'--daemon'*'--foreground'*'--stdout'*'--checks=24'*'--user=clamav'*'--config-file=/etc/clamav/freshclam-base2.conf'*) ;;
  *) exit 1 ;;
esac

for database in main daily bytecode; do
  database_file=''
  for suffix in cld cvd; do
    candidate="$database_root/$database.$suffix"
    if test -s "$candidate"; then
      database_file="$candidate"
      break
    fi
  done
  test -n "$database_file"
  sigtool --info "$database_file" | grep -Fqx 'Verification OK.'
done

version_line="$(clamscan --database="$database_root" --version)"
definition_version="$(printf '%s\n' "$version_line" | cut -d/ -f2)"
definition_date="$(printf '%s\n' "$version_line" | cut -d/ -f3-)"
case "$definition_version" in
  ''|*[!0-9]*) exit 1 ;;
esac
definition_epoch="$(date -u -D '%a %b %e %H:%M:%S %Y' -d "$definition_date" +%s)"
age_seconds="$((now_epoch - definition_epoch))"
test "$age_seconds" -ge -300
test "$age_seconds" -le "$maximum_age_seconds"

first_seen_epoch="$now_epoch"
if test -s "$state_file"; then
  read -r previous_version previous_first_seen <"$state_file"
  case "$previous_version:$previous_first_seen" in
    *[!0-9:]*|:*|*:) exit 1 ;;
  esac
  test "$definition_version" -ge "$previous_version"
  if test "$definition_version" -eq "$previous_version"; then
    first_seen_epoch="$previous_first_seen"
    test "$((now_epoch - first_seen_epoch))" -le "$maximum_age_seconds"
  fi
fi

temporary_state="$state_file.$$"
trap 'rm -f "$temporary_state"' EXIT HUP INT TERM
printf '%s %s\n' "$definition_version" "$first_seen_epoch" >"$temporary_state"
chmod 0600 "$temporary_state"
mv -f "$temporary_state" "$state_file"
trap - EXIT HUP INT TERM
