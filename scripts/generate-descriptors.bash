#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/generate-descriptors.bash [mod-name ...]

Generates mods/<mod-name>/descriptor.mod from mods/<mod-name>.mod,
omitting the launcher-only path attribute.
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mods_dir="$repo_root/mods"

generate_descriptor() {
  local mod_name="$1"
  local launcher_descriptor="$mods_dir/$mod_name.mod"
  local mod_dir="$mods_dir/$mod_name"
  local descriptor="$mod_dir/descriptor.mod"
  local tmp

  if [[ ! -f $launcher_descriptor ]]; then
    echo "error: launcher descriptor not found: $launcher_descriptor" >&2
    return 1
  fi

  if [[ ! -d $mod_dir ]]; then
    echo "error: mod directory not found: $mod_dir" >&2
    return 1
  fi

  tmp="$(mktemp "$mod_dir/.descriptor.mod.XXXXXX")"
  awk '!/^[[:space:]]*path[[:space:]]*=/' "$launcher_descriptor" > "$tmp"
  chmod 0644 "$tmp"
  mv -- "$tmp" "$descriptor"
  echo "Generated mods/$mod_name/descriptor.mod"
}

if [[ $# -gt 0 ]]; then
  for mod_name in "$@"; do
    generate_descriptor "$mod_name"
  done
else
  shopt -s nullglob
  launcher_descriptors=("$mods_dir"/*.mod)
  if [[ ${#launcher_descriptors[@]} -eq 0 ]]; then
    echo "error: no launcher descriptors found under $mods_dir" >&2
    exit 1
  fi

  for launcher_descriptor in "${launcher_descriptors[@]}"; do
    generate_descriptor "$(basename -- "$launcher_descriptor" .mod)"
  done
fi
