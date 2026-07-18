#!/usr/bin/env bash
# Synchronize local CK3 syntax references without committing copied game data.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/sync-ck3-references.bash [--check]

Copies `.info` files from $CK3_GAME_DIR and available script-doc logs from
$CK3_PARADOX_DIR/logs into references/generated/. The --check mode compares
the cache with those sources without writing anything.
EOF
}

check_only=0
case "${1:-}" in
  "") ;;
  --check) check_only=1 ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "error: unknown option: $1" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ -z ${CK3_GAME_DIR:-} ]]; then
  echo "error: CK3_GAME_DIR is not set" >&2
  exit 2
fi
if [[ -z ${CK3_PARADOX_DIR:-} ]]; then
  echo "error: CK3_PARADOX_DIR is not set" >&2
  exit 2
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
game_dir="$(realpath -- "$CK3_GAME_DIR")"
paradox_dir="$(realpath -- "$CK3_PARADOX_DIR")"
cache_root="$repo_root/references/generated"
info_destination="$cache_root/info"
docs_destination="$cache_root/script_docs"
manifest="$cache_root/manifest.json"
docs_source="$paradox_dir/logs"
declare -a script_docs=(effects.log event_scopes.log event_targets.log modifiers.log triggers.log)

if [[ ! -d $game_dir ]]; then
  echo "error: CK3_GAME_DIR is not a directory: $game_dir" >&2
  exit 2
fi

mapfile -t info_sources < <(find "$game_dir" -type f -name '*.info' -print | sort)
if [[ ${#info_sources[@]} -eq 0 ]]; then
  echo "error: no .info files found below CK3_GAME_DIR: $game_dir" >&2
  exit 1
fi

compare_file() {
  local source="$1"
  local destination="$2"
  if [[ ! -f $destination ]]; then
    echo "missing: ${destination#$cache_root/}" >&2
    return 1
  fi
  if ! cmp -s -- "$source" "$destination"; then
    echo "stale: ${destination#$cache_root/}" >&2
    return 1
  fi
}

if [[ $check_only -eq 1 ]]; then
  failed=0
  for source in "${info_sources[@]}"; do
    relative="${source#$game_dir/}"
    relative="${relative#game/}"
    if ! compare_file "$source" "$info_destination/$relative"; then
      failed=1
    fi
  done
  for filename in "${script_docs[@]}"; do
    source="$docs_source/$filename"
    if [[ -f $source ]] && ! compare_file "$source" "$docs_destination/$filename"; then
      failed=1
    fi
  done
  if [[ ! -f $manifest ]]; then
    echo "missing: manifest.json" >&2
    failed=1
  fi
  if [[ $failed -ne 0 ]]; then
    exit 1
  fi
  echo "CK3 reference cache is current (${#info_sources[@]} .info files)."
  exit 0
fi

mkdir -p "$info_destination" "$docs_destination"
for source in "${info_sources[@]}"; do
  relative="${source#$game_dir/}"
  relative="${relative#game/}"
  destination="$info_destination/$relative"
  mkdir -p "$(dirname -- "$destination")"
  cp -- "$source" "$destination"
done

copied_docs=0
for filename in "${script_docs[@]}"; do
  source="$docs_source/$filename"
  if [[ -f $source ]]; then
    cp -- "$source" "$docs_destination/$filename"
    copied_docs=$((copied_docs + 1))
  fi
done

if [[ $copied_docs -eq 0 ]]; then
  echo "warning: no script-doc logs found in $docs_source" >&2
  echo "warning: run CK3 in debug mode and issue the script_docs console command." >&2
fi

generated_at="$(date --iso-8601=seconds)"
cat >"$manifest" <<EOF
{
  "generated_at": "$generated_at",
  "game_dir": "$game_dir",
  "paradox_dir": "$paradox_dir",
  "info_files": ${#info_sources[@]},
  "script_doc_logs": $copied_docs
}
EOF

echo "Synchronized ${#info_sources[@]} .info files and $copied_docs script-doc logs."
