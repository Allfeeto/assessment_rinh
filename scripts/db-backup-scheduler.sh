#!/bin/sh
set -eu

log() {
    printf '%s %s\n' "$(date -Iseconds)" "$*"
}

run_backup() {
    kind=$1
    marker=$2
    state_file=$3

    last_marker=""
    if [ -f "$state_file" ]; then
        last_marker=$(cat "$state_file")
    fi

    if [ "$last_marker" = "$marker" ]; then
        return 0
    fi

    if sh /usr/local/bin/db-backup.sh "$kind"; then
        printf '%s\n' "$marker" > "$state_file"
    else
        log "ERROR: $kind backup failed; marker was not updated"
        return 1
    fi
}

backup_root=${BACKUP_DIR:-/backups}
state_dir="$backup_root/.state"
run_hour=${BACKUP_RUN_HOUR:-3}
run_minute=${BACKUP_RUN_MINUTE:-0}
weekly_day=${BACKUP_WEEKLY_DAY:-0}
monthly_day=${BACKUP_MONTHLY_DAY:-1}

umask 077
mkdir -p "$state_dir"
chmod 700 "$backup_root" "$state_dir"

log "Backup scheduler started: weekly_day=$weekly_day monthly_day=$monthly_day run_at=${run_hour}:${run_minute}"

while true; do
    current_hour=$(date +%H)
    current_minute=$(date +%M)

    if [ "$current_hour" = "$(printf '%02d' "$run_hour")" ] && [ "$current_minute" = "$(printf '%02d' "$run_minute")" ]; then
        current_weekday=$(date +%w)
        current_monthday=$(date +%-d)

        if [ "$current_weekday" = "$weekly_day" ]; then
            run_backup weekly "$(date +%G-W%V)" "$state_dir/weekly.last" || true
        fi

        if [ "$current_monthday" = "$monthly_day" ]; then
            run_backup monthly "$(date +%Y-%m)" "$state_dir/monthly.last" || true
        fi

        sleep 70
    else
        sleep 30
    fi
done
