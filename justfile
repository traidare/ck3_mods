default:
    @just --list

# Run pytest, optionally with additional arguments
test *args:
    pytest {{args}}

# Run Python lint checks
lint:
    ruff check .

# Format Python and repository prose/data files
format:
    ruff format .
    prettier --write "**/*.{json,md,markdown}" --ignore-path .gitignore --ignore-path .prettierignore --ignore-path $(git config --global core.excludesfile) --prose-wrap always

alias fmt := format
