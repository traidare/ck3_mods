// Package launcher is the one typed accessor for the Paradox Launcher
// database. It contains no command-line behaviour and never guesses a host
// path: callers pass the database resolved by internal/config.
package launcher

import (
	"database/sql"
	"fmt"
	"net/url"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	_ "modernc.org/sqlite"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
)

// DatabaseName is the Launcher's SQLite file.
const DatabaseName = "launcher-v2.sqlite"

// Error reports a Launcher database that is missing, unexpected, or unusable.
type Error struct{ Message string }

func (e *Error) Error() string { return e.Message }

func errorf(format string, arguments ...any) error {
	return &Error{Message: fmt.Sprintf(format, arguments...)}
}

// QuoteIdentifier escapes a SQLite identifier for interpolation.
func QuoteIdentifier(identifier string) string {
	return `"` + strings.ReplaceAll(identifier, `"`, `""`) + `"`
}

// DB is an open Launcher database together with its inspected schema.
type DB struct {
	handle         *sql.DB
	Path           string
	PlaysetColumns ColumnSet
	ModColumns     ColumnSet
	LinkColumns    ColumnSet
}

// Column describes one table column, including whether it must be supplied on
// insert.
type Column struct {
	Name       string
	NotNull    bool
	HasDefault bool
}

// ColumnSet indexes a table's columns by name.
type ColumnSet map[string]Column

// Has reports whether the table declares a column.
func (c ColumnSet) Has(name string) bool {
	_, ok := c[name]
	return ok
}

// Names returns the column names in sorted order.
func (c ColumnSet) Names() []string {
	names := make([]string, 0, len(c))
	for name := range c {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

// Open connects to the Launcher database and validates its schema.
func Open(path string, readonly bool) (*DB, error) {
	resolved := fsutil.MustAbs(path)
	if !fsutil.IsFile(resolved) {
		return nil, errorf("launcher database not found: %s", resolved)
	}

	// modernc.org/sqlite takes its options through the DSN query string.
	dsn := "file:" + url.PathEscape(filepath.ToSlash(resolved)) + "?_pragma=busy_timeout(3000)"
	if readonly {
		dsn += "&mode=ro"
	} else {
		dsn += "&_pragma=foreign_keys(1)"
	}
	handle, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, errorf("cannot open launcher database: %v", err)
	}
	// One connection keeps transactions and PRAGMA state coherent.
	handle.SetMaxOpenConns(1)

	database := &DB{handle: handle, Path: resolved}
	if err := database.inspectSchema(); err != nil {
		handle.Close()
		return nil, err
	}
	return database, nil
}

// Close releases the database handle.
func (d *DB) Close() error { return d.handle.Close() }

// Handle exposes the underlying connection for the few callers that need to
// run their own statements.
func (d *DB) Handle() *sql.DB { return d.handle }

func (d *DB) tableInfo(table string) (ColumnSet, error) {
	rows, err := d.handle.Query("PRAGMA table_info(" + QuoteIdentifier(table) + ")")
	if err != nil {
		return nil, errorf("cannot inspect %s: %v", table, err)
	}
	defer rows.Close()

	columns := ColumnSet{}
	for rows.Next() {
		var (
			index      int
			name       string
			columnType sql.NullString
			notNull    int
			dflt       sql.NullString
			primaryKey int
		)
		if err := rows.Scan(&index, &name, &columnType, &notNull, &dflt, &primaryKey); err != nil {
			return nil, errorf("cannot inspect %s: %v", table, err)
		}
		columns[name] = Column{Name: name, NotNull: notNull != 0, HasDefault: dflt.Valid}
	}
	return columns, rows.Err()
}

func (d *DB) inspectSchema() error {
	rows, err := d.handle.Query("SELECT name FROM sqlite_master WHERE type = 'table'")
	if err != nil {
		return errorf("cannot read the launcher schema: %v", err)
	}
	present := map[string]bool{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			rows.Close()
			return errorf("cannot read the launcher schema: %v", err)
		}
		present[name] = true
	}
	rows.Close()
	if err := rows.Err(); err != nil {
		return errorf("cannot read the launcher schema: %v", err)
	}

	var missingTables []string
	for _, table := range []string{"playsets", "mods", "playsets_mods"} {
		if !present[table] {
			missingTables = append(missingTables, table)
		}
	}
	if len(missingTables) > 0 {
		sort.Strings(missingTables)
		return errorf("unexpected launcher database; missing tables: %s", strings.Join(missingTables, ", "))
	}

	tables := []struct {
		name     string
		required []string
		into     *ColumnSet
	}{
		{"playsets", []string{"createdOn", "id", "name"}, &d.PlaysetColumns},
		{"mods", []string{"displayName", "id"}, &d.ModColumns},
		{"playsets_mods", []string{"enabled", "modId", "playsetId", "position"}, &d.LinkColumns},
	}
	for _, table := range tables {
		columns, err := d.tableInfo(table.name)
		if err != nil {
			return err
		}
		var missing []string
		for _, name := range table.required {
			if !columns.Has(name) {
				missing = append(missing, name)
			}
		}
		if len(missing) > 0 {
			sort.Strings(missing)
			return errorf("unexpected %s table schema; missing columns: %s",
				table.name, strings.Join(missing, ", "))
		}
		*table.into = columns
	}
	return nil
}

// Row is one query result addressed by column name. Values keep SQLite's
// dynamic typing, which varies across Launcher versions.
type Row map[string]any

// FirstValue returns the first of names that is present and non-empty.
func (r Row) FirstValue(names ...string) any {
	for _, name := range names {
		value, ok := r[name]
		if !ok || value == nil {
			continue
		}
		if text, isText := value.(string); isText && text == "" {
			continue
		}
		return value
	}
	return nil
}

// String returns the first present, non-empty value of names as text.
func (r Row) String(names ...string) string {
	return AsString(r.FirstValue(names...))
}

// AsString renders a SQLite value as text without scientific notation.
func AsString(value any) string {
	switch typed := value.(type) {
	case nil:
		return ""
	case string:
		return typed
	case []byte:
		return string(typed)
	case int64:
		return strconv.FormatInt(typed, 10)
	case float64:
		if typed == float64(int64(typed)) {
			return strconv.FormatInt(int64(typed), 10)
		}
		return strconv.FormatFloat(typed, 'g', -1, 64)
	case bool:
		if typed {
			return "1"
		}
		return "0"
	default:
		return fmt.Sprintf("%v", typed)
	}
}

// ParseEnabled interprets the several shapes the enabled column has taken.
// A missing value means enabled, matching the Launcher's own default.
func ParseEnabled(value any) bool {
	switch typed := value.(type) {
	case nil:
		return true
	case bool:
		return typed
	case int64:
		return typed != 0
	case float64:
		return typed != 0
	case string:
		switch strings.ToLower(strings.TrimSpace(typed)) {
		case "0", "false", "no", "off", "disabled":
			return false
		case "1", "true", "yes", "on", "enabled":
			return true
		}
		return typed != ""
	case []byte:
		return ParseEnabled(string(typed))
	}
	return false
}

// ParsePosition reads a load-order position, falling back to the row index.
func ParsePosition(value any, fallback int) int {
	switch typed := value.(type) {
	case int64:
		return int(typed)
	case float64:
		return int(typed)
	case string:
		if parsed, err := strconv.Atoi(strings.TrimSpace(typed)); err == nil {
			return parsed
		}
	case []byte:
		return ParsePosition(string(typed), fallback)
	}
	return fallback
}

func (d *DB) queryRows(query string, arguments ...any) ([]Row, error) {
	rows, err := d.handle.Query(query, arguments...)
	if err != nil {
		return nil, errorf("launcher query failed: %v", err)
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, errorf("launcher query failed: %v", err)
	}
	var result []Row
	for rows.Next() {
		cells := make([]any, len(columns))
		pointers := make([]any, len(columns))
		for index := range cells {
			pointers[index] = &cells[index]
		}
		if err := rows.Scan(pointers...); err != nil {
			return nil, errorf("launcher query failed: %v", err)
		}
		row := Row{}
		for index, name := range columns {
			row[name] = cells[index]
		}
		result = append(result, row)
	}
	return result, rows.Err()
}

// Query runs a read query and returns its rows by column name.
func (d *DB) Query(query string, arguments ...any) ([]Row, error) {
	return d.queryRows(query, arguments...)
}

// LivePlaysetClause excludes soft-deleted playsets on schemas that track them.
func (d *DB) LivePlaysetClause() string {
	if d.PlaysetColumns.Has("isRemoved") {
		return "COALESCE(isRemoved, 0) = 0"
	}
	return "1 = 1"
}

// SelectPlayset resolves one playset by name, or the active one when name is
// empty. Ambiguity is an error rather than an arbitrary pick.
func (d *DB) SelectPlayset(name string) (Row, error) {
	where := d.LivePlaysetClause()
	var arguments []any
	label := "active playset"
	if name != "" {
		where += " AND name = ?"
		arguments = append(arguments, name)
		label = fmt.Sprintf("playset named %q", name)
	} else {
		if !d.PlaysetColumns.Has("isActive") {
			return nil, errorf("the launcher schema cannot identify an active playset")
		}
		where += " AND COALESCE(isActive, 0) = 1"
	}

	rows, err := d.queryRows("SELECT * FROM playsets WHERE "+where, arguments...)
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, errorf("no %s was found", label)
	}
	if len(rows) > 1 {
		return nil, errorf("more than one %s was found", label)
	}
	return rows[0], nil
}

// PlaysetModRows returns a playset's mods in stored load order.
func (d *DB) PlaysetModRows(playsetID string) ([]Row, error) {
	return d.queryRows(`
		SELECT pm.enabled, pm.position, m.*
		FROM playsets_mods AS pm
		JOIN mods AS m ON m.id = pm.modId
		WHERE pm.playsetId = ?
		ORDER BY pm.position, m.id
	`, playsetID)
}

// DetectPdxUserID finds the Paradox account a new playset should belong to,
// preferring the active and most recently updated playset.
func (d *DB) DetectPdxUserID() (string, error) {
	if !d.PlaysetColumns.Has("pdxUserId") {
		return "", nil
	}
	var order []string
	if d.PlaysetColumns.Has("isActive") {
		order = append(order, "CASE WHEN COALESCE(isActive, 0) = 1 THEN 0 ELSE 1 END")
	}
	switch {
	case d.PlaysetColumns.Has("updatedOn") && d.PlaysetColumns.Has("createdOn"):
		order = append(order, "COALESCE(updatedOn, createdOn, 0) DESC")
	case d.PlaysetColumns.Has("createdOn"):
		order = append(order, "COALESCE(createdOn, 0) DESC")
	}
	clause := ""
	if len(order) > 0 {
		clause = " ORDER BY " + strings.Join(order, ", ")
	}

	rows, err := d.queryRows("SELECT pdxUserId FROM playsets " +
		"WHERE pdxUserId IS NOT NULL AND CAST(pdxUserId AS TEXT) <> ''" + clause + " LIMIT 1")
	if err != nil || len(rows) == 0 {
		return "", err
	}
	return AsString(rows[0]["pdxUserId"]), nil
}

// CreatePlayset inserts a new, inactive, locally owned playset and returns its
// identifier. A schema that requires a column this tool does not know about is
// an error, never a guess.
func (d *DB) CreatePlayset(execer interface {
	Exec(string, ...any) (sql.Result, error)
}, name, pdxUserID string,
) (string, error) {
	nowMillis := time.Now().UnixMilli()
	playsetID := NewUUID()
	known := map[string]any{
		"id":                           playsetID,
		"name":                         name,
		"isActive":                     0,
		"loadOrder":                    nil,
		"pdxId":                        nil,
		"pdxUserId":                    nullable(pdxUserID),
		"createdOn":                    nowMillis,
		"updatedOn":                    nowMillis,
		"syncedOn":                     nil,
		"deprecatedLastServerChecksum": nil,
		"lastServerChecksum":           nil,
		"isRemoved":                    0,
		"hasNotApprovedChanges":        0,
		"syncState":                    "NOT_ELIGIBLE",
		"state":                        "private",
		"owned":                        1,
		"author":                       "",
		"subscribersCount":             0,
		"ratingsCount":                 0,
		"thumbnailFileUrl":             nil,
		"description":                  "",
		"offDisk":                      0,
		"version":                      nil,
		"lastSyncAttemptAt":            nil,
	}

	var unsupported []string
	for name, column := range d.PlaysetColumns {
		if column.NotNull && !column.HasDefault {
			if _, ok := known[name]; !ok {
				unsupported = append(unsupported, name)
			}
		}
	}
	if len(unsupported) > 0 {
		sort.Strings(unsupported)
		return "", errorf("this launcher version has unsupported required playset columns: %s",
			strings.Join(unsupported, ", "))
	}

	names := make([]string, 0, len(known))
	for name := range known {
		if d.PlaysetColumns.Has(name) {
			names = append(names, name)
		}
	}
	sort.Strings(names)

	quoted := make([]string, len(names))
	placeholders := make([]string, len(names))
	values := make([]any, len(names))
	for index, name := range names {
		quoted[index] = QuoteIdentifier(name)
		placeholders[index] = "?"
		values[index] = known[name]
	}
	statement := "INSERT INTO playsets (" + strings.Join(quoted, ", ") +
		") VALUES (" + strings.Join(placeholders, ", ") + ")"
	if _, err := execer.Exec(statement, values...); err != nil {
		return "", errorf("cannot create playset: %v", err)
	}
	return playsetID, nil
}

// UpdateReplacedPlayset refreshes the bookkeeping columns of a playset whose
// contents are being replaced.
func (d *DB) UpdateReplacedPlayset(execer interface {
	Exec(string, ...any) (sql.Result, error)
}, playsetID string,
) error {
	var assignments []string
	var values []any
	if d.PlaysetColumns.Has("updatedOn") {
		assignments = append(assignments, "updatedOn = ?")
		values = append(values, time.Now().UnixMilli())
	}
	if d.PlaysetColumns.Has("isRemoved") {
		assignments = append(assignments, "isRemoved = 0")
	}
	if d.PlaysetColumns.Has("isActive") {
		assignments = append(assignments, "isActive = 0")
	}
	if len(assignments) == 0 {
		return nil
	}
	values = append(values, playsetID)
	_, err := execer.Exec("UPDATE playsets SET "+strings.Join(assignments, ", ")+" WHERE id = ?", values...)
	if err != nil {
		return errorf("cannot update playset: %v", err)
	}
	return nil
}

func nullable(value string) any {
	if value == "" {
		return nil
	}
	return value
}
