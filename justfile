default:
    @just --list

# Run the Go and Python lint checks
lint:
    unformatted="$(gofmt -l cmd internal)"; test -z "$unformatted" || { echo "gofmt: $unformatted" >&2; exit 1; }
    go vet ./...
    staticcheck ./...
    deadcode -test ./...
    ruff check .

# Run the Go tests
test:
    go test ./...
    PYTHONPATH=tools python -m unittest discover -s tests

# Format Go, Python, and repository prose/data files
format:
    gofumpt -w cmd internal
    ruff format .
    prettier --write "**/*.{json,md,markdown}" --ignore-path .gitignore --ignore-path .prettierignore --ignore-path $(git config --global core.excludesfile) --prose-wrap always

alias fmt := format
