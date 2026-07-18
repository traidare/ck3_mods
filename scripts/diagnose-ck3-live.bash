#!/usr/bin/env bash

set -u

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd -- "$script_dir/.." && pwd)
declare -a requested_pids=()
capture_backtrace=1
report_path=

usage() {
  cat <<'EOF'
Usage: scripts/diagnose-ck3-live.bash [options]

Options:
  --pid PID       Inspect this CK3 PID instead of relying on process discovery.
                  May be repeated.
  --output PATH   Write the report to PATH.
  --backtrace     Collect native backtraces (the default).
  --no-backtrace  Do not attach gdb.
  -h, --help      Show this help.

With no --output, the report is saved under the repository's shared .ignored/
directory. The script only reads process and game state.
EOF
}

while (($#)); do
  case $1 in
    --pid)
      if (($# < 2)) || [[ ! $2 =~ ^[0-9]+$ ]]; then
        printf '%s\n' '--pid requires a numeric PID' >&2
        exit 2
      fi
      requested_pids+=("$2")
      shift 2
      ;;
    --output)
      if (($# < 2)); then
        printf '%s\n' '--output requires a path' >&2
        exit 2
      fi
      report_path=$2
      shift 2
      ;;
    --backtrace)
      capture_backtrace=1
      shift
      ;;
    --no-backtrace)
      capture_backtrace=0
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -f "$repo_dir/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$repo_dir/.env"
  set +a
fi

if [[ -z ${CK3_PARADOX_DIR:-} ]]; then
  printf 'CK3_PARADOX_DIR is not set and could not be loaded from %s/.env\n' \
    "$repo_dir" >&2
  exit 1
fi

report_timestamp=$(date -u +%Y%m%dT%H%M%SZ)
report_path=${report_path:-"$repo_dir/.ignored/ck3-live-diagnose-$report_timestamp.txt"}
mkdir -p -- "$(dirname -- "$report_path")"

collect_diagnostics() {
  local ck3_pid
  local log_file
  local log_name
  local pass
  local pid_csv
  local steam_dir
  local steam_gameprocess_log
  local -a ck3_pids

  if ((${#requested_pids[@]})); then
    ck3_pids=("${requested_pids[@]}")
  else
    mapfile -t ck3_pids < <(
      for proc_dir in /proc/[0-9]*; do
        if [[ $(readlink "$proc_dir/exe" 2>/dev/null) == */ck3 ]]; then
          printf '%s\n' "${proc_dir##*/}"
        fi
      done
    )
  fi

  printf '=== TIME ===\n'
  date --iso-8601=seconds

  printf '=== CK3 PIDS ===\n'
  if ((${#ck3_pids[@]})); then
    for ck3_pid in "${ck3_pids[@]}"; do
      if [[ -d /proc/$ck3_pid ]]; then
        printf '%s\n' "$ck3_pid"
      else
        printf '%s (not visible under /proc)\n' "$ck3_pid"
      fi
    done
  else
    printf '<none>\n'
  fi

  if ((${#ck3_pids[@]})); then
    mapfile -t ck3_pids < <(
      for ck3_pid in "${ck3_pids[@]}"; do
        [[ -d /proc/$ck3_pid ]] && printf '%s\n' "$ck3_pid"
      done
    )
  fi

  if ((${#ck3_pids[@]})); then
    pid_csv=$(
      IFS=,
      printf '%s' "${ck3_pids[*]}"
    )

    for pass in 1 2; do
      printf '=== PROCESS SAMPLE %s ===\n' "$pass"
      date --iso-8601=seconds
      ps -p "$pid_csv" \
        -o pid,ppid,stat,lstart,etime,%cpu,%mem,rss,vsz,wchan:32,comm

      for ck3_pid in "${ck3_pids[@]}"; do
        printf '%s\n' "--- PID $ck3_pid executable ---"
        readlink "/proc/$ck3_pid/exe" 2>&1 || true

        printf '%s\n' "--- PID $ck3_pid relevant launch options ---"
        tr '\0' '\n' <"/proc/$ck3_pid/cmdline" 2>/dev/null |
          rg '^-debug_mode$|^-develop$|^--renderer=|^--no-sandbox$|^--ozone-platform=' ||
          true

        printf '%s\n' "--- PID $ck3_pid full command line ---"
        tr '\0' ' ' <"/proc/$ck3_pid/cmdline" 2>/dev/null || true
        printf '\n'

        printf '%s\n' "--- PID $ck3_pid status ---"
        sed -n -E \
          '/^(Name|State|VmPeak|VmSize|VmRSS|VmData|VmSwap|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):/p' \
          "/proc/$ck3_pid/status" 2>&1 || true

        printf '%s\n' "--- PID $ck3_pid I/O ---"
        cat "/proc/$ck3_pid/io" 2>&1 || true

        printf '%s\n' "--- PID $ck3_pid threads ---"
        ps -L -p "$ck3_pid" \
          -o pid,tid,psr,stat,%cpu,wchan:32,comm |
          head -n 80

        printf '%s\n' "--- PID $ck3_pid kernel stack ---"
        cat "/proc/$ck3_pid/stack" 2>&1 || true
      done

      printf '=== LOG SIZES %s ===\n' "$pass"
      for log_name in debug error game system; do
        log_file="$CK3_PARADOX_DIR/logs/$log_name.log"
        if [[ -f "$log_file" ]]; then
          stat -c '%n size=%s mtime=%y' "$log_file"
        fi
      done

      if ((pass == 1)); then
        sleep 5
      fi
    done

    if ((capture_backtrace)); then
      printf '=== NATIVE THREAD BACKTRACES ===\n'
      local -a gdb_command
      if command -v gdb >/dev/null 2>&1; then
        gdb_command=(gdb)
      elif command -v nix >/dev/null 2>&1; then
        gdb_command=(nix shell nixpkgs#gdb --command gdb)
      else
        gdb_command=()
      fi
      if ((${#gdb_command[@]})); then
        for ck3_pid in "${ck3_pids[@]}"; do
          printf '%s\n' "--- PID $ck3_pid gdb thread dump ---"
          timeout 60s "${gdb_command[@]}" --batch --quiet \
            -ex 'set pagination off' \
            -ex 'set print thread-events off' \
            -ex "attach $ck3_pid" \
            -ex 'thread 1' \
            -ex 'info registers rip rdi rsi rdx' \
            -ex 'x/s $rdi' \
            -ex 'x/s $rsi' \
            -ex 'x/s $rdx' \
            -ex 'info proc mappings' \
            -ex 'info threads' \
            -ex 'thread apply all bt' \
            -ex 'detach' 2>&1 || true
        done
      else
        printf 'gdb and nix are unavailable; cannot collect native backtraces\n'
      fi
    fi
  fi

  printf '=== DEBUG LOG TAIL ===\n'
  tail -n 120 "$CK3_PARADOX_DIR/logs/debug.log" 2>&1 || true

  printf '=== ERROR LOG TAIL ===\n'
  tail -n 120 "$CK3_PARADOX_DIR/logs/error.log" 2>&1 || true

  printf '=== NEWEST CRASH BUNDLES ===\n'
  if [[ -d "$CK3_PARADOX_DIR/crashes" ]]; then
    find "$CK3_PARADOX_DIR/crashes" -mindepth 1 -maxdepth 1 \
      -printf '%T@ %TY-%Tm-%Td %TH:%TM:%TS %f\n' |
      sort -nr |
      head -n 8
  fi

  printf '=== RECENT CK3 COREDUMPS ===\n'
  if command -v coredumpctl >/dev/null 2>&1; then
    coredumpctl --no-pager --since '-15 minutes' list ck3 2>&1 |
      tail -n 20 || true
  else
    printf 'coredumpctl is unavailable\n'
  fi

  printf '=== RECENT STEAM GAME-PROCESS LOG ===\n'
  if [[ -n ${CK3_WORKSHOP_DIR:-} ]]; then
    steam_dir=${CK3_WORKSHOP_DIR%%/steamapps/workshop/*}
    steam_gameprocess_log="$steam_dir/logs/gameprocess_log.txt"
  else
    steam_gameprocess_log=/var/lib/gaming/.local/share/Steam/logs/gameprocess_log.txt
  fi
  tail -n 120 "$steam_gameprocess_log" 2>&1 || true
}

collect_diagnostics | tee "$report_path"
printf 'Saved diagnostic report to %s\n' "$report_path"
