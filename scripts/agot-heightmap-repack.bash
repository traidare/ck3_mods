#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

load_repo_dotenv() {
  local variable
  declare -A existing=()
  for variable in CK3_PARADOX_DIR CK3_WORKSHOP_DIR CK3_GAME_DIR CK3_GAME; do
    if [[ -v $variable ]]; then
      existing["$variable"]="${!variable}"
    fi
  done

  if [[ -f $repo_root/.env ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$repo_root/.env"
    set +a
  fi

  for variable in "${!existing[@]}"; do
    printf -v "$variable" '%s' "${existing[$variable]}"
    export "${variable?}"
  done
}

load_repo_dotenv

default_workshop="${CK3_WORKSHOP_DIR:-}"
default_paradox="${CK3_PARADOX_DIR:-}"
staging_registry_id="mod/agot_heightmap_repack_staging.mod"
staging_mod_path="mod/agot_heightmap_repack_staging"
staging_name="AGOT Heightmap Repack Staging"

usage() {
  cat <<'EOF'
Usage:
  scripts/agot-heightmap-repack.bash prepare [options]
  scripts/agot-heightmap-repack.bash verify [options]
  scripts/agot-heightmap-repack.bash promote [options] --yes
  scripts/agot-heightmap-repack.bash import-playset [options] [--dry-run]
  scripts/agot-heightmap-repack.bash unregister [options]

See docs/agot-heightmap-repack.md for commands, options, safety constraints,
and the map-editor procedure.
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

note() {
  echo "$*"
}

absolute_path() {
  realpath -m -- "$1"
}

stage=""
workshop="$default_workshop"
paradox="$default_paradox"
register=yes
dry_run=no
confirmed=no

[[ $# -gt 0 ]] || {
  usage >&2
  exit 2
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
  usage
  exit 0
fi

command="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage)
      [[ $# -ge 2 ]] || die "--stage requires a directory"
      stage="$2"
      shift 2
      ;;
    --workshop-dir)
      [[ $# -ge 2 ]] || die "--workshop-dir requires a directory"
      workshop="$2"
      shift 2
      ;;
    --paradox-dir)
      [[ $# -ge 2 ]] || die "--paradox-dir requires a directory"
      paradox="$2"
      shift 2
      ;;
    --no-register)
      register=no
      shift
      ;;
    --dry-run)
      dry_run=yes
      shift
      ;;
    --yes)
      confirmed=yes
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -z $workshop ]] || workshop="$(absolute_path "$workshop")"
[[ -z $paradox ]] || paradox="$(absolute_path "$paradox")"
if [[ -z $stage ]]; then
  [[ -n $paradox ]] ||
    die "CK3_PARADOX_DIR is not set; configure it in .env or pass --paradox-dir and --stage"
  stage="$paradox/$staging_mod_path"
fi
stage="$(absolute_path "$stage")"
source_mod="$repo_root/mods/agot_now_lov_ee_map_compatch"
source_heightmap="$source_mod/content_source/heightmap/heightmap_now_delta_unpacked.png"
essos="${workshop:+$workshop/3682802751}"
launcher_descriptor="${paradox:+$paradox/$staging_registry_id}"
playset="$repo_root/.ignored/playsets/agot-heightmap-editor.json"
marker="$stage/.agot-heightmap-repack-stage"

write_staging_descriptor() {
  local destination="$1"
  local descriptor_path="${2:-}"
  local temporary
  temporary="$(mktemp "$(dirname -- "$destination")/.agot-heightmap-descriptor.XXXXXX")"
  {
    echo 'version="1.0.0"'
    echo "name=\"$staging_name\""
    echo 'supported_version="1.19.*"'
    echo 'tags={'
    echo '    "Map"'
    echo '    "Utilities"'
    echo '}'
    if [[ -n $descriptor_path ]]; then
      echo "path=\"$descriptor_path\""
    fi
  } >"$temporary"
  mv -- "$temporary" "$destination"
}

write_minimal_playset() {
  local temporary
  mkdir -p -- "$(dirname -- "$playset")"
  temporary="$(mktemp "$(dirname -- "$playset")/.agot-heightmap-playset.XXXXXX")"
  cat >"$temporary" <<'EOF'
{
  "game": "ck3",
  "name": "AGOT - Heightmap Editor (Minimal)",
  "mods": [
    {
      "displayName": "A Game of Thrones",
      "enabled": true,
      "position": 0,
      "steamId": "2962333032"
    },
    {
      "displayName": "AGOT Nobility of Westeros",
      "enabled": true,
      "position": 1,
      "steamId": "3664900993"
    },
    {
      "displayName": "Legacy of Valyria",
      "enabled": true,
      "position": 2,
      "steamId": "3403938445"
    },
    {
      "displayName": "Legacy of Valyria - AGOT 0.4.39 Temporary Compatch RC71",
      "enabled": true,
      "position": 3,
      "steamId": "3719888822"
    },
    {
      "displayName": "Essos Expanded",
      "enabled": true,
      "position": 4,
      "steamId": "3682802751"
    },
    {
      "displayName": "Essos Expanded - TempLoV Compatch",
      "enabled": true,
      "position": 5,
      "steamId": "3768149491"
    },
    {
      "displayName": "AGOT Heightmap Repack Staging",
      "enabled": true,
      "gameRegistryId": "mod/agot_heightmap_repack_staging.mod",
      "position": 6,
      "source": "local"
    }
  ]
}
EOF
  mv -- "$temporary" "$playset"
}

require_stage() {
  [[ -f $marker ]] || die "not a prepared staging directory: $stage"
  [[ -d $stage/map_data ]] || die "staging map_data directory is missing"
}

image_properties() {
  local image="$1"
  command -v identify >/dev/null 2>&1 ||
    die "ImageMagick identify is required to validate PNG metadata"
  identify -quiet -format '%w %h %z %[colorspace]' -- "$image"
}

verify_output() {
  local metadata properties source_expected source_actual source_reference
  local source_reference_actual source_pixels_expected source_pixels_actual
  local packed_before packed_after pixel_signature_before pixel_signature_after

  require_stage
  for file in \
    heightmap.png \
    heightmap.heightmap \
    packed_heightmap.png \
    indirection_heightmap.png; do
    [[ -s $stage/map_data/$file ]] ||
      die "missing or empty staging artifact: map_data/$file"
  done

  source_expected="$(awk '$2 == "map_data/heightmap.png" { print $1 }' \
    "$stage/pre-repack.sha256")"
  [[ -n $source_expected ]] || die "source hash is missing from pre-repack.sha256"
  source_reference="$stage/content_source/heightmap/heightmap_now_delta_unpacked.png"
  [[ -s $source_reference ]] ||
    die "preserved merged source is missing: $source_reference"
  source_reference_actual="$(sha256sum "$source_reference" | awk '{ print $1 }')"
  [[ $source_reference_actual == "$source_expected" ]] ||
    die "preserved merged source changed after preparation"
  source_actual="$(sha256sum "$stage/map_data/heightmap.png" | awk '{ print $1 }')"
  if [[ $source_actual != "$source_expected" ]]; then
    source_pixels_expected="$(identify -quiet -format '%#' -- "$source_reference")"
    source_pixels_actual="$(
      identify -quiet -format '%#' -- "$stage/map_data/heightmap.png"
    )"
    [[ $source_pixels_actual == "$source_pixels_expected" ]] ||
      die "heightmap.png pixels changed after preparation; refusing mixed input/output"
    note "The editor re-encoded heightmap.png without changing its decoded pixels."
  fi

  properties="$(image_properties "$stage/map_data/heightmap.png")"
  [[ $properties == "9216 6144 16 Gray" ]] ||
    die "unexpected heightmap.png properties: $properties (wanted: 9216 6144 16 Gray)"

  properties="$(image_properties "$stage/map_data/indirection_heightmap.png")"
  [[ $properties == 288\ 192\ * ]] ||
    die "unexpected indirection heightmap dimensions: $properties"

  properties="$(image_properties "$stage/map_data/packed_heightmap.png")"
  [[ $properties == *" 16 Gray" ]] ||
    die "unexpected packed heightmap properties: $properties"

  metadata="$(tr -d '\r' <"$stage/map_data/heightmap.heightmap")"
  [[ $metadata =~ original_heightmap_size=\{[[:space:]]*9216[[:space:]]+6144[[:space:]]*\} ]] ||
    die "heightmap.heightmap does not declare original size 9216 x 6144"
  [[ $metadata =~ tile_size=33([^0-9]|$) ]] ||
    die "heightmap.heightmap does not use the required 33 x 33 tile size"
  [[ $metadata =~ should_wrap_x=no([^[:alnum:]_]|$) ]] ||
    die "heightmap.heightmap unexpectedly enables horizontal map wrapping"
  [[ $metadata == *'heightmap_file="map_data/packed_heightmap.png"'* ]] ||
    die "heightmap.heightmap does not reference packed_heightmap.png"
  [[ $metadata == *'indirection_file="map_data/indirection_heightmap.png"'* ]] ||
    die "heightmap.heightmap does not reference indirection_heightmap.png"

  packed_before="$(awk '$2 == "map_data/packed_heightmap.png" { print $1 }' \
    "$stage/pre-repack.sha256")"
  packed_after="$(sha256sum "$stage/map_data/packed_heightmap.png" | awk '{ print $1 }')"
  [[ -n $packed_before ]] || die "seed packed-heightmap hash is missing"
  [[ $packed_after != "$packed_before" ]] ||
    die "packed_heightmap.png is still identical to the Essos Expanded seed; repack has not produced usable output"
  [[ -s $stage/pre-repack-packed-pixel-signature ]] ||
    die "seed packed-heightmap pixel signature is missing"
  pixel_signature_before="$(<"$stage/pre-repack-packed-pixel-signature")"
  pixel_signature_after="$(
    identify -quiet -format '%#' -- "$stage/map_data/packed_heightmap.png"
  )"
  [[ $pixel_signature_after != "$pixel_signature_before" ]] ||
    die "packed_heightmap.png was only re-encoded; its decoded elevation pixels are unchanged"

  note "Verified a coherent repack candidate in:"
  note "  $stage/map_data"
  note "The merged source is unchanged and the packed runtime data changed."
}

case "$command" in
  prepare)
    [[ -n $workshop ]] ||
      die "CK3_WORKSHOP_DIR is not set; configure it in .env or pass --workshop-dir"
    [[ ! -e $stage ]] ||
      die "staging path already exists; move it aside or choose another --stage: $stage"
    [[ -d $source_mod ]] || die "local map compatch is missing: $source_mod"
    [[ -f $source_heightmap ]] || die "merged source heightmap is missing: $source_heightmap"
    properties="$(image_properties "$source_heightmap")"
    [[ $properties == "9216 6144 16 Gray" ]] ||
      die "unexpected merged source properties: $properties"
    for file in heightmap.heightmap packed_heightmap.png indirection_heightmap.png; do
      [[ -f $essos/map_data/$file ]] ||
        die "Essos Expanded seed is missing: $essos/map_data/$file"
    done
    if [[ $register == yes ]]; then
      [[ -n $paradox ]] ||
        die "CK3_PARADOX_DIR is not set; configure it in .env or pass --paradox-dir"
      [[ -d $paradox ]] || die "CK3 user-data directory is missing: $paradox"
      expected_stage="$(absolute_path "$paradox/$staging_mod_path")"
      [[ $stage == "$expected_stage" ]] ||
        die "registered staging must be $expected_stage; use --no-register for a custom --stage"
      if [[ -e $launcher_descriptor ]] &&
        ! grep -Fq -- "name=\"$staging_name\"" "$launcher_descriptor"; then
        die "refusing to replace an unrelated launcher descriptor: $launcher_descriptor"
      fi
    fi

    mkdir -p -- "$stage"
    cp -a -- "$source_mod/." "$stage/"
    mkdir -p -- "$stage/map_data"
    cp -a -- "$source_heightmap" "$stage/map_data/heightmap.png"
    cp -a -- \
      "$essos/map_data/heightmap.heightmap" \
      "$essos/map_data/packed_heightmap.png" \
      "$essos/map_data/indirection_heightmap.png" \
      "$stage/map_data/"
    printf '%s\n' "AGOT heightmap repack staging directory" >"$marker"
    write_staging_descriptor "$stage/descriptor.mod"
    (
      cd -- "$stage"
      sha256sum \
        map_data/heightmap.png \
        map_data/heightmap.heightmap \
        map_data/packed_heightmap.png \
        map_data/indirection_heightmap.png \
        >pre-repack.sha256
    )
    identify -quiet -format '%#\n' -- "$stage/map_data/packed_heightmap.png" \
      >"$stage/pre-repack-packed-pixel-signature"
    write_minimal_playset

    if [[ $register == yes ]]; then
      mkdir -p -- "$paradox/mod"
      write_staging_descriptor "$launcher_descriptor" "$staging_mod_path"
      note "Registered temporary launcher descriptor:"
      note "  $launcher_descriptor"
    fi

    note "Prepared writable staging mod:"
    note "  $stage"
    note "Generated minimal editor playset:"
    note "  $playset"
    ;;

  verify)
    verify_output
    ;;

  promote)
    [[ $confirmed == yes ]] ||
      die "promotion changes the real local compatch; rerun with promote --yes"
    verify_output
    target="$repo_root/mods/agot_now_lov_ee_map_compatch/map_data"
    backup="$repo_root/.ignored/backup/heightmap-repack-backups/$(date -u +%Y%m%dT%H%M%SZ)"
    mkdir -p -- "$backup" "$target"
    for file in \
      heightmap.png \
      heightmap.heightmap \
      packed_heightmap.png \
      indirection_heightmap.png; do
      if [[ -f $target/$file ]]; then
        cp -a -- "$target/$file" "$backup/$file"
      fi
      install -m 0644 -- "$stage/map_data/$file" "$target/$file"
    done
    (
      cd -- "$target"
      sha256sum \
        heightmap.png \
        heightmap.heightmap \
        packed_heightmap.png \
        indirection_heightmap.png \
        >repacked-heightmap.sha256
    )
    note "Promoted the verified quartet into:"
    note "  $target"
    note "Previous local artifacts, when present, were backed up under:"
    note "  $backup"
    note "Essos Expanded's nodes.dat remains the runtime source."
    ;;

  import-playset)
    [[ -n $paradox ]] ||
      die "CK3_PARADOX_DIR is not set; configure it in .env or pass --paradox-dir"
    [[ -f $playset ]] || die "minimal playset file is missing: $playset"
    [[ -f $launcher_descriptor ]] ||
      die "staging launcher descriptor is not registered: $launcher_descriptor"
    args=(import "$playset")
    if [[ $dry_run == yes ]]; then
      args+=(--dry-run)
    fi
    CK3_PARADOX_DIR="$paradox" "$repo_root/scripts/ck3-playsets.py" "${args[@]}"
    ;;

  unregister)
    require_stage
    [[ -n $paradox ]] ||
      die "CK3_PARADOX_DIR is not set; configure it in .env or pass --paradox-dir"
    [[ -e $launcher_descriptor ]] || {
      note "Temporary launcher descriptor is already absent."
      exit 0
    }
    grep -Fq -- "path=\"$staging_mod_path\"" "$launcher_descriptor" ||
      die "refusing to move a descriptor that does not point at this stage"
    destination="$stage/agot_heightmap_repack_staging.mod.unregistered"
    [[ ! -e $destination ]] ||
      destination="$destination.$(date -u +%Y%m%dT%H%M%SZ)"
    mv -- "$launcher_descriptor" "$destination"
    note "Unregistered the staging mod without deleting it:"
    note "  $destination"
    ;;

  *)
    usage >&2
    exit 2
    ;;
esac
