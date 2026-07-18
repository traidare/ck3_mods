#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/sync-mods-to-launcher <launcher-mod-dir>
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mods_dir="$repo_root/mods"
dest_dir="$1"

if [[ ! -d "$mods_dir" ]]; then
  echo "error: mods directory not found: $mods_dir" >&2
  exit 1
fi

mkdir -p -- "$dest_dir"

shopt -s nullglob
launcher_mod_files=("$mods_dir"/*.mod)

if [[ ${#launcher_mod_files[@]} -eq 0 ]]; then
  echo "error: no launcher descriptors found under $mods_dir" >&2
  exit 1
fi

for launcher_mod_file in "${launcher_mod_files[@]}"; do
  mod_name="$(basename -- "$launcher_mod_file" .mod)"
  mod_dir="$mods_dir/$mod_name"

  if [[ ! -d "$mod_dir" ]]; then
    echo "error: missing mod directory for launcher descriptor: $mod_dir" >&2
    exit 1
  fi

  echo "Syncing $mod_name"
  rsync -av --copy-links --delete --exclude ck3-tiger.conf -- "$mod_dir/" "$dest_dir/$mod_name/"
  rsync -av --copy-links -- "$launcher_mod_file" "$dest_dir/$mod_name.mod"
done
