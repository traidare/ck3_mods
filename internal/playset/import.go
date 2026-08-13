package playset

import (
	"database/sql"
	"fmt"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/launcher"
)

// ResolvedMod is a portable playset entry matched to an installed mod row.
type ResolvedMod struct {
	ModID          string
	DisplayName    string
	Enabled        bool
	SourcePosition int
	SourceIndex    int
}

// ToMap renders the snake_case shape the Python dataclass produced.
func (r ResolvedMod) ToMap() map[string]any {
	return map[string]any{
		"mod_id":          r.ModID,
		"display_name":    r.DisplayName,
		"enabled":         r.Enabled,
		"source_position": r.SourcePosition,
		"source_index":    r.SourceIndex,
	}
}

// UnresolvedMod is a playset entry with no usable installed match.
type UnresolvedMod struct {
	SourceIndex int
	DisplayName string
	Reason      string
}

// ToMap renders the snake_case shape the Python dataclass produced.
func (u UnresolvedMod) ToMap() map[string]any {
	return map[string]any{
		"source_index": u.SourceIndex,
		"display_name": u.DisplayName,
		"reason":       u.Reason,
	}
}

// ImportPlan is what importing a portable playset would do to the Launcher.
type ImportPlan struct {
	Name              string
	Action            string
	Resolved          []ResolvedMod
	Unresolved        []UnresolvedMod
	ExistingPlaysetID string
	BackupPath        string
}

// ToMap renders the plan for JSON output.
func (p ImportPlan) ToMap() map[string]any {
	resolved := make([]any, len(p.Resolved))
	for index, mod := range p.Resolved {
		resolved[index] = mod.ToMap()
	}
	unresolved := make([]any, len(p.Unresolved))
	for index, mod := range p.Unresolved {
		unresolved[index] = mod.ToMap()
	}
	result := map[string]any{
		"name":       p.Name,
		"action":     p.Action,
		"resolved":   resolved,
		"unresolved": unresolved,
	}
	if p.BackupPath != "" {
		result["backupPath"] = p.BackupPath
	}
	return result
}

// candidateRows finds installed mods whose identity columns hold value. A nil
// result means the identity was not usable, which is different from an empty
// result meaning nothing matched.
func candidateRows(db *launcher.DB, columns []string, value string, localOnly bool) ([]launcher.Row, error) {
	var available []string
	for _, column := range columns {
		if db.ModColumns.Has(column) {
			available = append(available, column)
		}
	}
	if value == "" || len(available) == 0 {
		return nil, nil
	}

	predicates := make([]string, len(available))
	arguments := make([]any, len(available))
	for index, column := range available {
		predicates[index] = "CAST(" + launcher.QuoteIdentifier(column) + " AS TEXT) = ?"
		arguments[index] = value
	}
	where := "(" + strings.Join(predicates, " OR ") + ")"
	if localOnly && db.ModColumns.Has("source") {
		where += " AND source = 'local'"
	}
	status := "NULL AS status"
	if db.ModColumns.Has("status") {
		status = launcher.QuoteIdentifier("status")
	}
	rows, err := db.Query("SELECT id, displayName, "+status+" FROM mods WHERE "+where, arguments...)
	if err != nil {
		return nil, err
	}
	if rows == nil {
		rows = []launcher.Row{}
	}
	return rows, nil
}

// chooseCandidate picks the single usable row, preferring a lone ready mod
// when several rows share an identity.
func chooseCandidate(rows []launcher.Row) (launcher.Row, string) {
	seen := map[string]bool{}
	unique := make([]launcher.Row, 0, len(rows))
	for _, row := range rows {
		identifier := launcher.AsString(row["id"])
		if !seen[identifier] {
			seen[identifier] = true
			unique = append(unique, row)
		}
	}
	if len(unique) == 0 {
		return nil, "not installed or not yet scanned"
	}
	if len(unique) == 1 {
		return unique[0], ""
	}
	var ready []launcher.Row
	for _, row := range unique {
		if launcher.AsString(row["status"]) == "ready_to_play" {
			ready = append(ready, row)
		}
	}
	if len(ready) == 1 {
		return ready[0], ""
	}
	return nil, "ambiguous match"
}

func resolveMods(db *launcher.DB, playset Playset) ([]ResolvedMod, []UnresolvedMod, error) {
	var resolved []ResolvedMod
	var unresolved []UnresolvedMod
	seen := map[string]bool{}

	for index, mod := range playset.Mods {
		var rows []launcher.Row
		matchKind := "name"
		var err error

		if mod.Source == "local" && mod.GameRegistryID != "" {
			rows, err = candidateRows(db, []string{"gameRegistryId"}, mod.GameRegistryID, true)
			if err != nil {
				return nil, nil, err
			}
			matchKind = "local registry ID " + mod.GameRegistryID
		}
		if rows == nil && mod.SteamID != "" {
			rows, err = candidateRows(db, []string{"steamId", "remoteSteamId"}, mod.SteamID, false)
			if err != nil {
				return nil, nil, err
			}
			matchKind = "Steam ID " + mod.SteamID
		}
		if rows == nil && mod.PdxID != "" {
			rows, err = candidateRows(db, []string{"pdxId", "remotePdxId"}, mod.PdxID, false)
			if err != nil {
				return nil, nil, err
			}
			matchKind = "Paradox ID " + mod.PdxID
		}
		if rows == nil {
			rows, err = candidateRows(db, []string{"displayName", "name"}, mod.DisplayName, false)
			if err != nil {
				return nil, nil, err
			}
		}

		candidate, reason := chooseCandidate(rows)
		if candidate == nil {
			unresolved = append(unresolved, UnresolvedMod{
				SourceIndex: index,
				DisplayName: mod.DisplayName,
				Reason:      reason + " (" + matchKind + ")",
			})
			continue
		}
		modID := launcher.AsString(candidate["id"])
		if seen[modID] {
			unresolved = append(unresolved, UnresolvedMod{
				SourceIndex: index,
				DisplayName: mod.DisplayName,
				Reason:      "duplicate mod",
			})
			continue
		}
		seen[modID] = true

		displayName := launcher.AsString(candidate["displayName"])
		if displayName == "" {
			displayName = mod.DisplayName
		}
		resolved = append(resolved, ResolvedMod{
			ModID:          modID,
			DisplayName:    displayName,
			Enabled:        mod.Enabled,
			SourcePosition: mod.Position,
			SourceIndex:    index,
		})
	}

	sort.SliceStable(resolved, func(left, right int) bool {
		if resolved[left].SourcePosition != resolved[right].SourcePosition {
			return resolved[left].SourcePosition < resolved[right].SourcePosition
		}
		return resolved[left].SourceIndex < resolved[right].SourceIndex
	})
	return resolved, unresolved, nil
}

// PlanImport derives what importing this playset would change, reading only.
func PlanImport(databasePath string, playset Playset) (ImportPlan, error) {
	db, err := launcher.Open(databasePath, true)
	if err != nil {
		return ImportPlan{}, err
	}
	defer db.Close()
	return planImport(db, playset)
}

func planImport(db *launcher.DB, playset Playset) (ImportPlan, error) {
	if len([]rune(playset.Name)) > 255 {
		return ImportPlan{}, fmt.Errorf("playset name exceeds the launcher's 255-character limit")
	}
	resolved, unresolved, err := resolveMods(db, playset)
	if err != nil {
		return ImportPlan{}, err
	}

	where := db.LivePlaysetClause() + " AND name = ?"
	existing, err := db.Query("SELECT id FROM playsets WHERE "+where, playset.Name)
	if err != nil {
		return ImportPlan{}, err
	}
	if len(existing) > 1 {
		return ImportPlan{}, fmt.Errorf("more than one non-removed playset is named %q", playset.Name)
	}

	plan := ImportPlan{
		Name:       playset.Name,
		Action:     "create",
		Resolved:   resolved,
		Unresolved: unresolved,
	}
	if len(existing) == 1 {
		plan.ExistingPlaysetID = launcher.AsString(existing[0]["id"])
		plan.Action = "replace"
	}
	return plan, nil
}

// ApplyImport writes the playset into the Launcher database, after taking a
// backup. It refuses to drop unresolved mods unless allowMissing says so.
func ApplyImport(databasePath string, playset Playset, allowMissing bool) (ImportPlan, error) {
	plan, err := PlanImport(databasePath, playset)
	if err != nil {
		return ImportPlan{}, err
	}
	if len(plan.Unresolved) > 0 && !allowMissing {
		return ImportPlan{}, fmt.Errorf("import has %d unresolved mod(s); pass --allow-missing to omit them",
			len(plan.Unresolved))
	}

	backupPath, err := launcher.Backup(databasePath)
	if err != nil {
		return ImportPlan{}, err
	}

	db, err := launcher.Open(databasePath, false)
	if err != nil {
		return ImportPlan{}, err
	}
	defer db.Close()

	if err := writeImport(db, plan); err != nil {
		return ImportPlan{}, fmt.Errorf("playset import failed; database backup is %s: %w", backupPath, err)
	}
	plan.BackupPath = backupPath
	return plan, nil
}

func writeImport(db *launcher.DB, plan ImportPlan) error {
	// The accessor holds a single connection, so every read has to happen
	// before the transaction claims it.
	var pdxUserID string
	if plan.ExistingPlaysetID == "" {
		detected, err := db.DetectPdxUserID()
		if err != nil {
			return err
		}
		pdxUserID = detected
	}

	transaction, err := db.Handle().Begin()
	if err != nil {
		return err
	}
	committed := false
	defer func() {
		if !committed {
			_ = transaction.Rollback()
		}
	}()

	execer := transactionExecer{transaction}
	playsetID := plan.ExistingPlaysetID
	if playsetID != "" {
		if err := db.UpdateReplacedPlayset(execer, playsetID); err != nil {
			return err
		}
		if _, err := transaction.Exec("DELETE FROM playsets_mods WHERE playsetId = ?", playsetID); err != nil {
			return err
		}
	} else {
		playsetID, err = db.CreatePlayset(execer, plan.Name, pdxUserID)
		if err != nil {
			return err
		}
	}

	statement, err := transaction.Prepare(
		"INSERT INTO playsets_mods (playsetId, modId, enabled, position) VALUES (?, ?, ?, ?)")
	if err != nil {
		return err
	}
	defer statement.Close()
	for position, mod := range plan.Resolved {
		enabled := 0
		if mod.Enabled {
			enabled = 1
		}
		if _, err := statement.Exec(playsetID, mod.ModID, enabled, position); err != nil {
			return err
		}
	}

	if err := transaction.Commit(); err != nil {
		return err
	}
	committed = true
	return nil
}

// transactionExecer adapts a transaction to the Exec interface the launcher
// helpers take, so a create or replace runs inside one atomic unit.
type transactionExecer struct{ transaction *sql.Tx }

func (t transactionExecer) Exec(query string, arguments ...any) (sql.Result, error) {
	return t.transaction.Exec(query, arguments...)
}
