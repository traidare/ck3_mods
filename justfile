set dotenv-load := true

# Install mods to local game installation
install:
    scripts/sync-mods-to-launcher.bash "${CK3_PARADOX_DIR}/mod"

# Generate descriptor.mod files from top-level launcher descriptors
generate-descriptors *mods:
    scripts/generate-descriptors.bash {{mods}}

# Run Tiger against all local mods, or one mod path/name if provided
check-tiger mod="":
    #!/usr/bin/env bash
    mod='{{mod}}'
    if [[ -n "$mod" ]]; then
        scripts/check-tiger.bash "$mod"
    else
        scripts/check-tiger.bash
    fi

# Diff two playset files
diff-playsets from to:
    dyff between \
        --omit-header \
        --additional-identifier steamId \
        --ignore-order-changes \
        --exclude-regexp '^mods\..*\.position$' \
        {{from}} {{to}}

prettier:
    prettier --write "**/*.{json,md,markdown}" --ignore-path .gitignore --ignore-path .prettierignore --ignore-path $(git config --global core.excludesfile) --prose-wrap always

ruff-format:
    ruff format .

format: prettier ruff-format
alias fmt := format
