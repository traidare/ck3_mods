package preserve

import (
	"archive/zip"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/launcher"
)

// copyFile copies one planned file and returns its digest. The source is
// re-checked before and after the copy: a mod updated mid-run must fail rather
// than land in the snapshot half old and half new.
func copyFile(entry FileEntry, destination string) (string, error) {
	before, err := os.Stat(entry.SourcePath)
	if err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}
	if before.Size() != entry.Size || before.ModTime().UnixNano() != entry.ModTimeNanos {
		return "", fmt.Errorf("source changed after preflight: %s", entry.SourcePath)
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}

	digest := sha256.New()
	source, err := os.Open(entry.SourcePath)
	if err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}
	defer source.Close()
	target, err := os.OpenFile(destination, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}
	if _, err := io.Copy(io.MultiWriter(target, digest), source); err != nil {
		target.Close()
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}
	if err := target.Close(); err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}

	if err := os.Chmod(destination, before.Mode().Perm()); err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}
	if err := os.Chtimes(destination, before.ModTime(), before.ModTime()); err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}

	after, err := os.Stat(entry.SourcePath)
	if err != nil {
		return "", fmt.Errorf("could not copy %s: %w", entry.SourcePath, err)
	}
	if after.Size() != entry.Size || after.ModTime().UnixNano() != entry.ModTimeNanos {
		return "", fmt.Errorf("source changed while being copied: %s", entry.SourcePath)
	}
	return hex.EncodeToString(digest.Sum(nil)), nil
}

// extractArchive writes every planned member of a ZIP-distributed mod.
func extractArchive(mod *SourceMod, destination string, hashes map[string]string) error {
	reader, err := zip.OpenReader(mod.SourcePath)
	if err != nil {
		return fmt.Errorf("could not extract %s: %w", mod.SourcePath, err)
	}
	defer reader.Close()

	members := map[string]*zip.File{}
	for _, member := range reader.File {
		members[member.Name] = member
	}
	for _, entry := range mod.ZipEntries {
		member, found := members[entry.MemberName]
		if !found {
			return fmt.Errorf("could not extract %s: missing member %s", mod.SourcePath, entry.MemberName)
		}
		target := filepath.Join(destination, filepath.FromSlash(entry.RelativePath))
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return fmt.Errorf("could not extract %s: %w", mod.SourcePath, err)
		}
		source, err := member.Open()
		if err != nil {
			return fmt.Errorf("could not extract %s: %w", mod.SourcePath, err)
		}
		output, err := os.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
		if err != nil {
			source.Close()
			return fmt.Errorf("could not extract %s: %w", mod.SourcePath, err)
		}
		digest := sha256.New()
		_, copyErr := io.Copy(io.MultiWriter(output, digest), source)
		source.Close()
		closeErr := output.Close()
		if copyErr != nil {
			return fmt.Errorf("could not extract %s: %w", mod.SourcePath, copyErr)
		}
		if closeErr != nil {
			return fmt.Errorf("could not extract %s: %w", mod.SourcePath, closeErr)
		}
		info, err := os.Stat(target)
		if err != nil {
			return fmt.Errorf("could not extract %s: %w", mod.SourcePath, err)
		}
		if info.Size() != entry.Size {
			return fmt.Errorf("ZIP member changed size while extracting: %s", entry.MemberName)
		}
		hashes[entry.RelativePath] = hex.EncodeToString(digest.Sum(nil))
	}
	return nil
}

// copyMod materializes one mod under the staging root and returns the Launcher
// registry descriptor that will point at its final location.
func copyMod(mod *SourceMod, destination, finalRelativePath string) (string, error) {
	if err := os.MkdirAll(destination, 0o755); err != nil {
		return "", fmt.Errorf("could not create %s: %w", destination, err)
	}

	hashes := map[string]string{}
	if mod.SourceKind == "directory" {
		for _, entry := range mod.Files {
			digest, err := copyFile(entry, filepath.Join(destination, filepath.FromSlash(entry.RelativePath)))
			if err != nil {
				return "", err
			}
			hashes[entry.RelativePath] = digest
		}
	} else if err := extractArchive(mod, destination, hashes); err != nil {
		return "", err
	}

	descriptor := transformDescriptor(mod.DescriptorText, "")
	descriptorPath := filepath.Join(destination, "descriptor.mod")
	if err := os.WriteFile(descriptorPath, []byte(descriptor), 0o644); err != nil {
		return "", fmt.Errorf("could not write %s: %w", descriptorPath, err)
	}
	hashes["descriptor.mod"] = fsutil.Sha256Bytes([]byte(descriptor))

	// One digest over every path and file digest, so the manifest records the
	// snapshot's content rather than each file individually.
	relatives := make([]string, 0, len(hashes))
	for relative := range hashes {
		relatives = append(relatives, relative)
	}
	sort.Strings(relatives)
	combined := sha256.New()
	for _, relative := range relatives {
		combined.Write([]byte(relative))
		combined.Write([]byte{0})
		combined.Write([]byte(hashes[relative]))
		combined.Write([]byte{'\n'})
	}
	mod.ContentSHA256 = hex.EncodeToString(combined.Sum(nil))
	return transformDescriptor(mod.DescriptorText, finalRelativePath), nil
}

// registryDescriptorFile is one Launcher descriptor the snapshot publishes.
type registryDescriptorFile struct {
	Filename string
	Content  string
}

// temporaryName builds a unique hidden name beside a final one, so a failed
// run leaves nothing the Launcher would try to load.
func temporaryName(prefix string) string {
	var random [16]byte
	if _, err := io.ReadFull(rand.Reader, random[:]); err != nil {
		return prefix + strconv.FormatInt(time.Now().UnixNano(), 16) + ".tmp"
	}
	return prefix + hex.EncodeToString(random[:]) + ".tmp"
}

// writeJSONAtomic replaces path with data, never leaving a partial manifest.
func writeJSONAtomic(path string, value any) error {
	data, err := jsonout.Marshal(value)
	if err != nil {
		return err
	}
	temporary := filepath.Join(filepath.Dir(path), temporaryName("."+filepath.Base(path)+"."))
	if err := os.WriteFile(temporary, data, 0o644); err != nil {
		os.Remove(temporary)
		return fmt.Errorf("could not write %s: %w", path, err)
	}
	if err := os.Rename(temporary, path); err != nil {
		os.Remove(temporary)
		return fmt.Errorf("could not write %s: %w", path, err)
	}
	return nil
}

// writeTextExclusive creates a file that must not already exist.
func writeTextExclusive(path, content string) error {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return fmt.Errorf("could not create %s: %w", path, err)
	}
	if _, err := file.WriteString(content); err != nil {
		file.Close()
		os.Remove(path)
		return fmt.Errorf("could not create %s: %w", path, err)
	}
	if err := file.Close(); err != nil {
		os.Remove(path)
		return fmt.Errorf("could not create %s: %w", path, err)
	}
	return nil
}

// stage builds the whole snapshot beside its final location, so a failure
// leaves nothing the Launcher can see.
func (p *Plan) stage() (string, []registryDescriptorFile, error) {
	staging := filepath.Join(p.ModDirectory, temporaryName("."+p.SnapshotSlug+"."))
	if err := os.Mkdir(staging, 0o755); err != nil {
		return "", nil, fmt.Errorf("could not create %s: %w", staging, err)
	}

	var registries []registryDescriptorFile
	for _, mod := range p.Mods {
		finalRelative := "mod/" + p.SnapshotSlug + "/" + mod.CloneName
		content, err := copyMod(mod, filepath.Join(staging, mod.CloneName), finalRelative)
		if err != nil {
			os.RemoveAll(staging)
			return "", nil, err
		}
		registries = append(registries, registryDescriptorFile{Filename: mod.RegistryFilename, Content: content})
	}
	if err := writeTextExclusive(filepath.Join(staging, "README.txt"), p.readme()); err != nil {
		os.RemoveAll(staging)
		return "", nil, err
	}
	if err := writeJSONAtomic(filepath.Join(staging, "snapshot.json"), p.manifest(false, nil)); err != nil {
		os.RemoveAll(staging)
		return "", nil, err
	}
	return staging, registries, nil
}

// publish moves the staged snapshot into place and registers its descriptors.
func (p *Plan) publish(staging string, registries []registryDescriptorFile) error {
	if err := os.Rename(staging, p.FinalRoot); err != nil {
		os.RemoveAll(staging)
		return fmt.Errorf("could not publish snapshot under %s: %w", p.ModDirectory, err)
	}
	var created []string
	for _, descriptor := range registries {
		target := filepath.Join(p.ModDirectory, descriptor.Filename)
		if err := writeTextExclusive(target, descriptor.Content); err != nil {
			for _, path := range created {
				os.Remove(path)
			}
			os.RemoveAll(p.FinalRoot)
			return err
		}
		created = append(created, target)
	}
	return nil
}

// backupDatabase copies the Launcher database before the snapshot is
// registered, under a name that says which operation took it.
func (p *Plan) backupDatabase(timestamp string) (string, error) {
	backupPath := p.DatabasePath + ".preserve-" + timestamp + ".bak"
	if _, err := os.Lstat(backupPath); err == nil {
		return "", fmt.Errorf("database backup already exists: %s", backupPath)
	}
	if err := launcher.BackupTo(p.DatabasePath, backupPath); err != nil {
		return "", err
	}
	return backupPath, nil
}

// insertLocalMod adds one snapshot clone to the Launcher's mod table.
func insertLocalMod(execer transactionExecer, columns launcher.ColumnSet, plan *Plan, mod *SourceMod, nowMillis int64) (string, error) {
	modID := launcher.NewUUID()
	name := mod.Row["name"]
	if launcher.AsString(name) == "" {
		name = mod.DisplayName
	}
	tags := mod.Row["tags"]
	if launcher.AsString(tags) == "" {
		tags = "[]"
	}
	known := map[string]any{
		"id":                    modID,
		"pdxId":                 nil,
		"steamId":               nil,
		"gameRegistryId":        "mod/" + mod.RegistryFilename,
		"name":                  name,
		"displayName":           mod.DisplayName,
		"descriptionDeprecated": mod.Row["descriptionDeprecated"],
		"thumbnailUrl":          nil,
		"thumbnailPath":         nil,
		"version":               mod.Row["version"],
		"tags":                  tags,
		"requiredVersion":       mod.Row["requiredVersion"],
		"arch":                  mod.Row["arch"],
		"os":                    mod.Row["os"],
		"repositoryPath":        nil,
		"dirPath":               filepath.Join(plan.FinalRoot, mod.CloneName),
		"archivePath":           nil,
		"status":                "ready_to_play",
		"source":                "local",
		"cause":                 nil,
		"timeUpdated":           nowMillis,
		"isNew":                 1,
		"createdDate":           nowMillis,
		"subscribedDate":        nowMillis,
		"size":                  mod.ByteCount,
		"metadataId":            nil,
		"remotePdxId":           nil,
		"remoteSteamId":         nil,
		"metadataVersion":       nil,
		"isMetadataApplied":     0,
		"metadataStatus":        "not_applied",
		"metadataGameId":        nil,
		"descriptionPdx":        nil,
		"descriptionSteam":      nil,
		"shortDescriptionPdx":   nil,
		"keepLatest":            0,
		"userVersion":           nil,
		"remotePdxUserId":       nil,
		"remoteSteamUserId":     nil,
	}

	names := make([]string, 0, len(known))
	for name := range known {
		if columns.Has(name) {
			names = append(names, name)
		}
	}
	sort.Strings(names)

	quoted := make([]string, len(names))
	placeholders := make([]string, len(names))
	values := make([]any, len(names))
	for index, name := range names {
		quoted[index] = launcher.QuoteIdentifier(name)
		placeholders[index] = "?"
		values[index] = known[name]
	}
	statement := "INSERT INTO mods (" + strings.Join(quoted, ", ") + ") VALUES (" +
		strings.Join(placeholders, ", ") + ")"
	if _, err := execer.Exec(statement, values...); err != nil {
		return "", fmt.Errorf("cannot register snapshot mod %q: %w", mod.DisplayName, err)
	}
	mod.NewModID = modID
	return modID, nil
}

// currentFingerprint re-reads the source playset inside the write transaction.
func currentFingerprint(transaction *sql.Tx, db *launcher.DB, plan *Plan) ([]fingerprintEntry, error) {
	row := transaction.QueryRow(
		"SELECT id FROM playsets WHERE id = ? AND "+db.LivePlaysetClause(), plan.SourcePlaysetID)
	var identifier any
	if err := row.Scan(&identifier); err != nil {
		return nil, fmt.Errorf("source playset disappeared or was removed during the copy")
	}

	rows, err := transaction.Query(`
		SELECT pm.enabled, pm.position, m.id
		FROM playsets_mods AS pm
		JOIN mods AS m ON m.id = pm.modId
		WHERE pm.playsetId = ?
		ORDER BY pm.position, m.id
	`, plan.SourcePlaysetID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var fingerprint []fingerprintEntry
	index := 0
	for rows.Next() {
		var enabled, position, modID any
		if err := rows.Scan(&enabled, &position, &modID); err != nil {
			return nil, err
		}
		if !launcher.ParseEnabled(enabled) {
			continue
		}
		fingerprint = append(fingerprint, fingerprintEntry{
			ModID:    launcher.AsString(modID),
			Position: launcher.ParsePosition(position, index),
		})
		index++
	}
	return fingerprint, rows.Err()
}

func sameFingerprint(left, right []fingerprintEntry) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

// transactionExecer adapts a transaction to the Exec interface the launcher
// helpers take, so the whole registration is one atomic unit.
type transactionExecer struct{ transaction *sql.Tx }

func (t transactionExecer) Exec(query string, arguments ...any) (sql.Result, error) {
	return t.transaction.Exec(query, arguments...)
}

// register records the published snapshot as a new Launcher playset.
func (p *Plan) register() (string, string, error) {
	_, backupTimestamp := timestamps(time.Now())
	backupPath, err := p.backupDatabase(backupTimestamp)
	if err != nil {
		return "", "", err
	}

	db, err := launcher.Open(p.DatabasePath, false)
	if err != nil {
		return "", backupPath, err
	}
	defer db.Close()
	if err := validateModInsertSchema(db.ModColumns); err != nil {
		return "", backupPath, err
	}

	// The accessor holds a single connection, so every read that does not go
	// through the transaction has to happen before it claims that connection.
	pdxUserID, err := db.DetectPdxUserID()
	if err != nil {
		return "", backupPath, err
	}

	transaction, err := db.Handle().Begin()
	if err != nil {
		return "", backupPath, err
	}
	committed := false
	defer func() {
		if !committed {
			_ = transaction.Rollback()
		}
	}()

	fingerprint, err := currentFingerprint(transaction, db, p)
	if err != nil {
		return "", backupPath, err
	}
	if !sameFingerprint(fingerprint, p.SourceFingerprint) {
		return "", backupPath, fmt.Errorf("source playset changed during the copy; database registration aborted")
	}

	conflict := transaction.QueryRow(
		"SELECT 1 FROM playsets WHERE "+db.LivePlaysetClause()+" AND name = ? LIMIT 1", p.SnapshotName)
	var present any
	if err := conflict.Scan(&present); err == nil {
		return "", backupPath, fmt.Errorf("a live playset named %q now exists", p.SnapshotName)
	} else if err != sql.ErrNoRows {
		return "", backupPath, err
	}

	execer := transactionExecer{transaction}
	nowMillis := time.Now().UnixMilli()
	modIDs := make([]string, len(p.Mods))
	for index, mod := range p.Mods {
		modID, err := insertLocalMod(execer, db.ModColumns, p, mod, nowMillis)
		if err != nil {
			return "", backupPath, err
		}
		modIDs[index] = modID
	}

	playsetID, err := db.CreatePlayset(execer, p.SnapshotName, pdxUserID)
	if err != nil {
		return "", backupPath, err
	}
	for position, modID := range modIDs {
		if _, err := transaction.Exec(
			"INSERT INTO playsets_mods (playsetId, modId, enabled, position) VALUES (?, ?, 1, ?)",
			playsetID, modID, position); err != nil {
			return "", backupPath, err
		}
	}

	if err := transaction.Commit(); err != nil {
		return "", backupPath, err
	}
	committed = true
	return playsetID, backupPath, nil
}

// Apply copies the planned content and registers it with the Launcher.
func (p *Plan) Apply() (Result, error) {
	if _, err := os.Lstat(p.FinalRoot); err == nil {
		return Result{}, fmt.Errorf("snapshot directory already exists: %s", p.FinalRoot)
	}
	for _, mod := range p.Mods {
		descriptor := filepath.Join(p.ModDirectory, mod.RegistryFilename)
		if _, err := os.Lstat(descriptor); err == nil {
			return Result{}, fmt.Errorf("launcher descriptor already exists: %s", descriptor)
		}
	}

	staging, registries, err := p.stage()
	if err != nil {
		return Result{}, err
	}
	if err := p.publish(staging, registries); err != nil {
		return Result{}, err
	}
	playsetID, backupPath, err := p.register()
	if err != nil {
		return Result{BackupPath: backupPath}, err
	}
	if err := writeJSONAtomic(filepath.Join(p.FinalRoot, "snapshot.json"), p.manifest(true, playsetID)); err != nil {
		return Result{PlaysetID: playsetID, BackupPath: backupPath}, err
	}
	return Result{PlaysetID: playsetID, BackupPath: backupPath}, nil
}
