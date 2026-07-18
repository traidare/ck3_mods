#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/check-tiger.bash [mod-name-or-path ...]

With no arguments, checks every local mod under mods/.

Environment:
  CK3_GAME_DIR      CK3 installation directory.
  CK3_PARADOX_DIR   CK3 launcher/user-data directory.
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

resolve_path() {
  local path="$1"
  if [[ $path = /* ]]; then
    realpath -m -- "$path"
  else
    realpath -m -- "$repo_root/$path"
  fi
}

if [[ -z ${CK3_GAME_DIR:-} ]]; then
  echo "error: CK3_GAME_DIR is not set" >&2
  exit 2
fi

if [[ -z ${CK3_PARADOX_DIR:-} ]]; then
  echo "error: CK3_PARADOX_DIR is not set" >&2
  exit 2
fi

rel_path() {
  local path="$1"
  realpath --relative-to="$repo_root" -- "$path" 2>/dev/null || printf '%s\n' "$path"
}

find_descriptor() {
  local ref="$1"
  local candidate mod_name descriptor

  for candidate in "$ref" "$repo_root/$ref" "$repo_root/mods/$ref"; do
    if [[ -d $candidate ]]; then
      descriptor="$candidate/descriptor.mod"
      if [[ -f $descriptor ]]; then
        realpath -- "$descriptor"
        return 0
      fi

      echo "error: missing descriptor.mod in mod directory: $candidate" >&2
      return 1
    fi

    if [[ -f $candidate ]]; then
      if [[ $(basename -- "$candidate") == "descriptor.mod" ]]; then
        realpath -- "$candidate"
        return 0
      fi

      if [[ $candidate == *.mod ]]; then
        mod_name="$(basename -- "$candidate" .mod)"
        descriptor="$(dirname -- "$candidate")/$mod_name/descriptor.mod"
        if [[ -f $descriptor ]]; then
          realpath -- "$descriptor"
          return 0
        fi
        echo "error: launcher descriptor has no matching mod descriptor: $candidate -> $descriptor" >&2
        return 1
      fi
    fi
  done

  echo "error: could not resolve mod descriptor or directory: $ref" >&2
  return 1
}

check_descriptor() {
  local descriptor="$1"
  local mod_dir config
  local -a tiger_args

  mod_dir="$(dirname -- "$descriptor")"
  config="$mod_dir/ck3-tiger.conf"

  echo "Checking $(rel_path "$descriptor")"
  tiger_args=(
    --no-color
    --consolidate
    --game "$(resolve_path "$CK3_GAME_DIR")"
    --paradox "$(resolve_path "$CK3_PARADOX_DIR")"
  )
  if [[ -f $config ]]; then
    tiger_args+=(--config "$config")
  fi
  tiger_args+=("$descriptor")

  ck3-tiger "${tiger_args[@]}"
}

declare -a descriptors=()
if [[ $# -eq 0 ]]; then
  mapfile -t descriptors < <(find "$repo_root/mods" -mindepth 2 -maxdepth 2 -type f -name descriptor.mod -print0 | xargs -0 -r realpath | sort -u)
else
  for ref in "$@"; do
    descriptors+=("$(find_descriptor "$ref")")
  done
fi

if [[ ${#descriptors[@]} -eq 0 ]]; then
  echo "error: no mod descriptors found" >&2
  exit 1
fi

for descriptor in "${descriptors[@]}"; do
  check_descriptor "$descriptor"
done
