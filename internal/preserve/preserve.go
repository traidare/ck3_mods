// Package preserve makes an update-proof private copy of every enabled mod in
// a playset, and registers that copy as a new Launcher playset.
//
// Planning validates sources, collisions, schema, and free space without
// writing anything; Apply is the only mutating operation.
package preserve

import (
	"archive/zip"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"syscall"
	"time"
	"unicode"

	"golang.org/x/text/unicode/norm"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/launcher"
	"codeberg.org/traidare/ck3_mods/internal/layers"
	"codeberg.org/traidare/ck3_mods/internal/playset"
)

// ManifestFormat identifies the snapshot.json shape written into every
// snapshot directory.
const ManifestFormat = "ck3-playset-snapshot-v1"

// oneGiB is the smallest free-space margin a snapshot is allowed to leave.
const oneGiB = 1 << 30

// goodStatuses are the Launcher statuses whose content is safe to copy.
var goodStatuses = map[string]bool{"ready_to_play": true, "initialized": true}

// skippedDirectories are never copied into a snapshot.
var skippedDirectories = map[string]bool{".git": true}

// descriptorPathKeys are the host-specific fields a snapshot descriptor drops.
var descriptorPathKeys = []string{"archive", "path", "remote_file_id"}

// Error reports an expected validation or preservation failure.
type Error struct{ Message string }

func (e *Error) Error() string { return e.Message }

func errorf(format string, arguments ...any) error {
	return &Error{Message: fmt.Sprintf(format, arguments...)}
}

// FileEntry is one regular file found under a mod's source directory. Size and
// ModTimeNanos are recorded during planning and re-checked while copying, so a
// mod updated mid-run cannot be preserved half old and half new.
type FileEntry struct {
	RelativePath string
	SourcePath   string
	Size         int64
	ModTimeNanos int64
}

// ZipEntry is one member of a mod distributed as an archive.
type ZipEntry struct {
	RelativePath string
	MemberName   string
	Size         int64
}

// SourceMod is one enabled playset entry together with the content behind it.
type SourceMod struct {
	SourceIndex      int
	SourcePosition   int
	ModID            string
	DisplayName      string
	Source           string
	RegistryID       string
	DescriptorPath   string
	DescriptorText   string
	SourceKind       string
	SourcePath       string
	Row              launcher.Row
	CloneName        string
	RegistryFilename string
	Files            []FileEntry
	ZipEntries       []ZipEntry
	ByteCount        int64
	FileCount        int
	ContentSHA256    string
	NewModID         string
}

// fingerprintEntry pins one enabled mod to its load position, so registration
// can refuse a playset that changed while its content was being copied.
type fingerprintEntry struct {
	ModID    string
	Position int
}

// Plan is a validated description of one preservation run.
type Plan struct {
	DatabasePath      string
	ParadoxDirectory  string
	ModDirectory      string
	WorkshopDirectory string
	SourcePlaysetID   string
	SourcePlaysetName string
	SelectionSource   string
	SnapshotName      string
	SnapshotSlug      string
	CreatedAt         string
	FinalRoot         string
	Mods              []*SourceMod
	SourceFingerprint []fingerprintEntry
	RequiredBytes     int64
	FreeBytes         int64
}

// ContentBytes is the total size of the content the snapshot would copy.
func (p *Plan) ContentBytes() int64 {
	var total int64
	for _, mod := range p.Mods {
		total += mod.ByteCount
	}
	return total
}

// ToMap renders the plan for JSON output.
func (p *Plan) ToMap() map[string]any {
	return map[string]any{
		"sourcePlayset":     p.SourcePlaysetName,
		"selectionSource":   p.SelectionSource,
		"snapshotName":      p.SnapshotName,
		"snapshotDirectory": p.FinalRoot,
		"enabledMods":       len(p.Mods),
		"contentBytes":      p.ContentBytes(),
		"requiredBytes":     p.RequiredBytes,
		"freeBytes":         p.FreeBytes,
	}
}

// Result reports what a completed run created.
type Result struct {
	PlaysetID  string
	BackupPath string
}

// timestamps renders the two clock formats a snapshot needs: one for humans
// and manifests, one that is safe inside a filename.
func timestamps(moment time.Time) (string, string) {
	utc := moment.UTC()
	return utc.Format("2006-01-02T15:04:05Z"), utc.Format("20060102T150405Z")
}

var nonAlphanumeric = regexp.MustCompile(`[^A-Za-z0-9]+`)

// slugify renders a name as a filesystem-safe identifier, matching the Python
// original: decompose, drop everything non-ASCII, then collapse separators.
func slugify(value, fallback string, limit int) string {
	var ascii strings.Builder
	for _, character := range norm.NFKD.String(value) {
		if character < unicode.MaxASCII {
			ascii.WriteRune(character)
		}
	}
	slug := strings.ToLower(strings.Trim(nonAlphanumeric.ReplaceAllString(ascii.String(), "-"), "-"))
	if slug == "" {
		slug = fallback
	}
	if len(slug) > limit {
		slug = slug[:limit]
	}
	if slug = strings.TrimRight(slug, "-"); slug == "" {
		return fallback
	}
	return slug
}

// expandUser resolves a leading ~ the way the Launcher database sometimes
// stores it.
func expandUser(value string) string {
	if value != "~" && !strings.HasPrefix(value, "~/") {
		return value
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return value
	}
	return filepath.Join(home, strings.TrimPrefix(strings.TrimPrefix(value, "~"), "/"))
}

func resolvePath(value string) string {
	resolved, err := filepath.EvalSymlinks(fsutil.MustAbs(value))
	if err != nil {
		return fsutil.MustAbs(value)
	}
	return resolved
}

// descriptorValue reads one quoted scalar out of descriptor text. The snapshot
// only needs the host-path fields, so this stays line-based rather than
// parsing the descriptor and losing its formatting.
func descriptorValue(text, key string) string {
	pattern := regexp.MustCompile(`^\s*` + regexp.QuoteMeta(key) + `\s*=\s*"((?:\\.|[^"\\])*)"`)
	for _, line := range strings.Split(strings.ReplaceAll(text, "\r\n", "\n"), "\n") {
		if match := pattern.FindStringSubmatch(line); match != nil {
			return strings.ReplaceAll(strings.ReplaceAll(match[1], `\"`, `"`), `\\`, `\`)
		}
	}
	return ""
}

var descriptorPathLine = regexp.MustCompile(`^\s*(?:` + strings.Join(descriptorPathKeys, "|") + `)\s*=`)

// transformDescriptor strips the host-specific fields from a descriptor and,
// for a Launcher registry copy, appends the snapshot's own path.
func transformDescriptor(text, launcherPath string) string {
	normalized := strings.ReplaceAll(strings.ReplaceAll(text, "\r\n", "\n"), "\r", "\n")
	var retained []string
	for _, line := range strings.Split(strings.TrimSuffix(normalized, "\n"), "\n") {
		if !descriptorPathLine.MatchString(line) {
			retained = append(retained, line)
		}
	}
	for len(retained) > 0 && strings.TrimSpace(retained[len(retained)-1]) == "" {
		retained = retained[:len(retained)-1]
	}
	if launcherPath != "" {
		escaped := strings.ReplaceAll(strings.ReplaceAll(launcherPath, `\`, `\\`), `"`, `\"`)
		retained = append(retained, `path="`+escaped+`"`)
	}
	return strings.Join(retained, "\n") + "\n"
}

// registryDescriptor resolves a Launcher registry ID to a readable file.
func registryDescriptor(paradoxDirectory, registryID string) string {
	if registryID == "" {
		return ""
	}
	resolved, err := layers.SafeRegistryPath(paradoxDirectory, registryID)
	if err != nil || !fsutil.IsFile(resolved) {
		return ""
	}
	return resolved
}

// resolveDescriptor finds the descriptor describing a mod, preferring the
// Launcher's own registry copy over the one shipped inside the content.
func resolveDescriptor(row launcher.Row, paradoxDirectory, sourceDirectory string) (string, string, error) {
	candidates := []string{registryDescriptor(paradoxDirectory, row.String("gameRegistryId"))}
	if sourceDirectory != "" {
		candidates = append(candidates, filepath.Join(sourceDirectory, "descriptor.mod"))
	}
	for _, candidate := range candidates {
		if candidate == "" || !fsutil.IsFile(candidate) {
			continue
		}
		text, err := fsutil.ReadTextBOM(candidate)
		if err != nil {
			return "", "", errorf("could not read descriptor %s: %v", candidate, err)
		}
		return candidate, text, nil
	}
	return "", "", errorf("no readable descriptor was found for %q", row.String("displayName", "name"))
}

// pathFromDescriptor resolves a host path a descriptor declares, relative to
// the Paradox directory when it is not absolute.
func pathFromDescriptor(text, paradoxDirectory, key string) string {
	value := descriptorValue(text, key)
	if value == "" {
		return ""
	}
	candidate := expandUser(value)
	if !filepath.IsAbs(candidate) {
		candidate = filepath.Join(paradoxDirectory, candidate)
	}
	if _, err := os.Stat(candidate); err != nil {
		return ""
	}
	return candidate
}

// resolveSource locates the installed content of one mod, which the Launcher
// records inconsistently across versions and installation kinds.
func resolveSource(row launcher.Row, paradoxDirectory, workshopDirectory string) (kind, sourcePath, descriptorPath, descriptorText string, err error) {
	if directory := row.String("dirPath"); directory != "" {
		if expanded := expandUser(directory); fsutil.IsDir(expanded) {
			descriptorPath, descriptorText, err = resolveDescriptor(row, paradoxDirectory, expanded)
			if err != nil {
				return "", "", "", "", err
			}
			return "directory", resolvePath(expanded), descriptorPath, descriptorText, nil
		}
	}

	descriptorPath, descriptorText, err = resolveDescriptor(row, paradoxDirectory, "")
	if err != nil {
		return "", "", "", "", err
	}
	if declared := pathFromDescriptor(descriptorText, paradoxDirectory, "path"); fsutil.IsDir(declared) {
		return "directory", resolvePath(declared), descriptorPath, descriptorText, nil
	}

	// A local mod whose registry entry is mod/<name>.mod conventionally keeps
	// its content in the matching mod/<name>/ directory.
	registryID := row.String("gameRegistryId")
	if strings.ToLower(row.String("source")) == "local" && registryID != "" {
		relative := strings.ReplaceAll(registryID, `\`, "/")
		if strings.HasSuffix(relative, ".mod") {
			if inferred, pathErr := layers.SafeRegistryPath(paradoxDirectory, strings.TrimSuffix(relative, ".mod")); pathErr == nil && fsutil.IsDir(inferred) {
				return "directory", resolvePath(inferred), descriptorPath, descriptorText, nil
			}
		}
	}

	if steamID := row.String("steamId", "remoteSteamId"); workshopDirectory != "" && steamID != "" {
		if inferred := filepath.Join(workshopDirectory, steamID); fsutil.IsDir(inferred) {
			return "directory", resolvePath(inferred), descriptorPath, descriptorText, nil
		}
	}

	archive := ""
	if value := row.String("archivePath"); value != "" {
		archive = expandUser(value)
	}
	if !fsutil.IsFile(archive) {
		archive = pathFromDescriptor(descriptorText, paradoxDirectory, "archive")
	}
	if fsutil.IsFile(archive) {
		reader, zipErr := zip.OpenReader(archive)
		if zipErr != nil {
			return "", "", "", "", errorf("unsupported non-ZIP mod archive: %s", archive)
		}
		reader.Close()
		return "zip", resolvePath(archive), descriptorPath, descriptorText, nil
	}

	return "", "", "", "", errorf("could not resolve installed content for %q", row.String("displayName", "name"))
}

// treeEntry is one file discovered while walking a mod directory.
type treeEntry struct {
	relative string
	physical string
	size     int64
	modTime  int64
}

type inode struct {
	device uint64
	number uint64
}

func inodeOf(info os.FileInfo) (inode, bool) {
	stat, ok := info.Sys().(*syscall.Stat_t)
	if !ok {
		return inode{}, false
	}
	return inode{device: uint64(stat.Dev), number: uint64(stat.Ino)}, true
}

// walkTree lists every regular file below root, following symbolic links the
// way CK3 itself would and refusing anything it cannot copy faithfully.
func walkTree(root string) ([]treeEntry, error) {
	var entries []treeEntry

	var visit func(physical, logical string, ancestors map[inode]bool) error
	visit = func(physical, logical string, ancestors map[inode]bool) error {
		info, err := os.Stat(physical)
		if err != nil {
			return errorf("could not inspect %s: %v", physical, err)
		}
		current, hasInode := inodeOf(info)

		if info.IsDir() {
			if hasInode && ancestors[current] {
				return errorf("cyclic directory link found at %s", physical)
			}
			children, err := os.ReadDir(physical)
			if err != nil {
				return errorf("could not list %s: %v", physical, err)
			}
			nested := make(map[inode]bool, len(ancestors)+1)
			for key := range ancestors {
				nested[key] = true
			}
			if hasInode {
				nested[current] = true
			}
			for _, child := range children {
				if skippedDirectories[child.Name()] {
					continue
				}
				childLogical := child.Name()
				if logical != "" {
					childLogical = logical + "/" + child.Name()
				}
				if err := visit(filepath.Join(physical, child.Name()), childLogical, nested); err != nil {
					return err
				}
			}
			return nil
		}
		if info.Mode().IsRegular() {
			entries = append(entries, treeEntry{
				relative: logical,
				physical: resolvePath(physical),
				size:     info.Size(),
				modTime:  info.ModTime().UnixNano(),
			})
			return nil
		}
		return errorf("unsupported special file in mod content: %s", physical)
	}

	if err := visit(root, "", map[inode]bool{}); err != nil {
		return nil, err
	}
	return entries, nil
}

var drivePrefix = regexp.MustCompile(`^[A-Za-z]:`)

// safeZipPath rejects archive members that would escape the snapshot.
func safeZipPath(name string) (string, error) {
	normalized := strings.ReplaceAll(name, `\`, "/")
	if strings.HasPrefix(normalized, "/") || drivePrefix.MatchString(normalized) {
		return "", errorf("unsafe path in ZIP archive: %s", name)
	}
	var parts []string
	for _, part := range strings.Split(normalized, "/") {
		if part == ".." {
			return "", errorf("unsafe path in ZIP archive: %s", name)
		}
		if part != "" && part != "." {
			parts = append(parts, part)
		}
	}
	if len(parts) == 0 {
		return "", errorf("unsafe path in ZIP archive: %s", name)
	}
	return strings.Join(parts, "/"), nil
}

// scanSource records what a mod's content consists of, without reading it.
func scanSource(mod *SourceMod) error {
	if mod.SourceKind == "directory" {
		entries, err := walkTree(mod.SourcePath)
		if err != nil {
			return err
		}
		mod.Files = make([]FileEntry, 0, len(entries))
		for _, entry := range entries {
			mod.Files = append(mod.Files, FileEntry{
				RelativePath: entry.relative,
				SourcePath:   entry.physical,
				Size:         entry.size,
				ModTimeNanos: entry.modTime,
			})
		}
		sort.Slice(mod.Files, func(left, right int) bool {
			return mod.Files[left].RelativePath < mod.Files[right].RelativePath
		})
		mod.FileCount = len(mod.Files)
		for _, entry := range mod.Files {
			mod.ByteCount += entry.Size
		}
		return nil
	}

	reader, err := zip.OpenReader(mod.SourcePath)
	if err != nil {
		return errorf("could not inspect ZIP archive %s: %v", mod.SourcePath, err)
	}
	defer reader.Close()

	seen := map[string]bool{}
	for _, member := range reader.File {
		relative, err := safeZipPath(member.Name)
		if err != nil {
			return err
		}
		if strings.HasSuffix(strings.ReplaceAll(member.Name, `\`, "/"), "/") {
			continue
		}
		skip := false
		for _, part := range strings.Split(relative, "/") {
			if skippedDirectories[part] {
				skip = true
			}
		}
		if skip {
			continue
		}
		if member.Mode()&os.ModeSymlink != 0 {
			return errorf("symbolic links in ZIP archives are unsupported: %s", member.Name)
		}
		if seen[relative] {
			return errorf("duplicate destination path in ZIP archive: %s", relative)
		}
		seen[relative] = true
		mod.ZipEntries = append(mod.ZipEntries, ZipEntry{
			RelativePath: relative,
			MemberName:   member.Name,
			Size:         int64(member.UncompressedSize64),
		})
	}
	sort.Slice(mod.ZipEntries, func(left, right int) bool {
		return mod.ZipEntries[left].RelativePath < mod.ZipEntries[right].RelativePath
	})
	mod.FileCount = len(mod.ZipEntries)
	for _, entry := range mod.ZipEntries {
		mod.ByteCount += entry.Size
	}
	return nil
}

// sourceIdentifier is the stable name a clone directory is derived from.
func sourceIdentifier(row launcher.Row, fallback string) string {
	if registry := row.String("gameRegistryId"); registry != "" {
		base := path.Base(strings.ReplaceAll(registry, `\`, "/"))
		return strings.TrimSuffix(base, path.Ext(base))
	}
	if remote := row.String("steamId", "remoteSteamId", "pdxId", "remotePdxId"); remote != "" {
		return remote
	}
	return fallback
}

// insertableModColumns are the mod columns this tool knows how to fill. A
// schema that requires anything else is an error rather than a guess.
var insertableModColumns = []string{
	"arch", "archivePath", "cause", "createdDate", "descriptionDeprecated",
	"descriptionPdx", "descriptionSteam", "dirPath", "displayName",
	"gameRegistryId", "id", "isMetadataApplied", "isNew", "keepLatest",
	"metadataGameId", "metadataId", "metadataStatus", "metadataVersion",
	"name", "os", "pdxId", "remotePdxId", "remotePdxUserId", "remoteSteamId",
	"remoteSteamUserId", "repositoryPath", "requiredVersion",
	"shortDescriptionPdx", "size", "source", "status", "steamId",
	"subscribedDate", "tags", "thumbnailPath", "thumbnailUrl", "timeUpdated",
	"userVersion", "version",
}

func validateModInsertSchema(columns launcher.ColumnSet) error {
	known := map[string]bool{}
	for _, name := range insertableModColumns {
		known[name] = true
	}
	var unsupported []string
	for name, column := range columns {
		if column.NotNull && !column.HasDefault && !known[name] {
			unsupported = append(unsupported, name)
		}
	}
	if len(unsupported) > 0 {
		sort.Strings(unsupported)
		return errorf("this launcher version has unsupported required mod columns: %s",
			strings.Join(unsupported, ", "))
	}
	return nil
}

// Options are the inputs of one preservation run.
type Options struct {
	DatabasePath      string
	ModDirectory      string
	WorkshopDirectory string
	PlaysetName       string
	ConfiguredName    string
	SnapshotName      string
	Now               time.Time
}

// Build validates a preservation run and describes it without writing.
func Build(options Options) (*Plan, error) {
	databasePath := resolvePath(expandUser(options.DatabasePath))
	paradoxDirectory := filepath.Dir(databasePath)
	modDirectory := resolvePath(expandUser(options.ModDirectory))
	if !fsutil.IsDir(modDirectory) {
		return nil, errorf("launcher mod directory not found: %s", modDirectory)
	}
	workshopDirectory := ""
	if options.WorkshopDirectory != "" {
		workshopDirectory = resolvePath(expandUser(options.WorkshopDirectory))
	}

	moment := options.Now
	if moment.IsZero() {
		moment = time.Now()
	}
	createdAt, filenameTimestamp := timestamps(moment)
	requestedName, selectionSource := playset.RequestedName(options.PlaysetName, options.ConfiguredName)

	db, err := launcher.Open(databasePath, true)
	if err != nil {
		return nil, err
	}
	defer db.Close()
	if err := validateModInsertSchema(db.ModColumns); err != nil {
		return nil, err
	}

	source, err := db.SelectPlayset(requestedName)
	if err != nil {
		return nil, err
	}
	sourceName := launcher.AsString(source["name"])

	snapshotName := strings.TrimSpace(options.SnapshotName)
	if options.SnapshotName == "" {
		snapshotName = fmt.Sprintf("%s (preserved %s)", sourceName, createdAt)
	}
	if snapshotName == "" {
		return nil, errorf("snapshot name cannot be empty")
	}
	if len([]rune(snapshotName)) > 255 {
		return nil, errorf("snapshot name exceeds the launcher's 255-character limit")
	}

	existing, err := db.Query("SELECT 1 FROM playsets WHERE "+db.LivePlaysetClause()+" AND name = ? LIMIT 1", snapshotName)
	if err != nil {
		return nil, err
	}
	if len(existing) > 0 {
		return nil, errorf("a live playset named %q already exists", snapshotName)
	}

	rows, err := db.PlaysetModRows(launcher.AsString(source["id"]))
	if err != nil {
		return nil, err
	}
	var enabledRows []launcher.Row
	for _, row := range rows {
		if launcher.ParseEnabled(row["enabled"]) {
			enabledRows = append(enabledRows, row)
		}
	}
	if len(enabledRows) == 0 {
		return nil, errorf("playset %q has no enabled mods", sourceName)
	}

	slugSource := options.SnapshotName
	if slugSource == "" {
		slugSource = fmt.Sprintf("%s-%s", sourceName, filenameTimestamp)
	}
	snapshotSlug := slugify(slugSource, "snapshot", 80)
	finalRoot := filepath.Join(modDirectory, snapshotSlug)
	if _, err := os.Lstat(finalRoot); err == nil {
		return nil, errorf("snapshot directory already exists: %s", finalRoot)
	}

	width := len(fmt.Sprint(len(enabledRows) - 1))
	if width < 3 {
		width = 3
	}

	plan := &Plan{
		DatabasePath:      databasePath,
		ParadoxDirectory:  paradoxDirectory,
		ModDirectory:      modDirectory,
		WorkshopDirectory: workshopDirectory,
		SourcePlaysetID:   launcher.AsString(source["id"]),
		SourcePlaysetName: sourceName,
		SelectionSource:   selectionSource,
		SnapshotName:      snapshotName,
		SnapshotSlug:      snapshotSlug,
		CreatedAt:         createdAt,
		FinalRoot:         finalRoot,
	}

	for index, row := range enabledRows {
		displayName := row.String("displayName", "name")
		if displayName == "" {
			displayName = fmt.Sprintf("mod %d", index)
		}
		status := row.String("status")
		if !goodStatuses[status] {
			return nil, errorf("mod %q has unusable Launcher status %q", displayName, status)
		}
		kind, sourcePath, descriptorPath, descriptorText, err := resolveSource(row, paradoxDirectory, workshopDirectory)
		if err != nil {
			return nil, err
		}

		cloneName := fmt.Sprintf("%0*d-%s", width, index,
			slugify(sourceIdentifier(row, displayName), "mod", 64))
		registryFilename := fmt.Sprintf("%s__%0*d.mod", snapshotSlug, width, index)
		if _, err := os.Lstat(filepath.Join(modDirectory, registryFilename)); err == nil {
			return nil, errorf("launcher descriptor already exists: %s",
				filepath.Join(modDirectory, registryFilename))
		}

		position := launcher.ParsePosition(row["position"], index)
		mod := &SourceMod{
			SourceIndex:      index,
			SourcePosition:   position,
			ModID:            launcher.AsString(row["id"]),
			DisplayName:      displayName,
			Source:           row.String("source"),
			RegistryID:       row.String("gameRegistryId"),
			DescriptorPath:   descriptorPath,
			DescriptorText:   descriptorText,
			SourceKind:       kind,
			SourcePath:       sourcePath,
			Row:              row,
			CloneName:        cloneName,
			RegistryFilename: registryFilename,
		}
		if err := scanSource(mod); err != nil {
			return nil, err
		}
		plan.Mods = append(plan.Mods, mod)
		plan.SourceFingerprint = append(plan.SourceFingerprint,
			fingerprintEntry{ModID: mod.ModID, Position: position})
	}

	contentBytes := plan.ContentBytes()
	margin := (contentBytes + 19) / 20
	if margin < oneGiB {
		margin = oneGiB
	}
	plan.RequiredBytes = contentBytes + margin
	available, err := freeBytes(modDirectory)
	if err != nil {
		return nil, err
	}
	plan.FreeBytes = available
	if available < plan.RequiredBytes {
		return nil, errorf("not enough free space under %s: need %d bytes, have %d bytes",
			modDirectory, plan.RequiredBytes, available)
	}
	return plan, nil
}

// manifest renders snapshot.json, whose key order is part of the format.
func (p *Plan) manifest(registered bool, playsetID any) jsonout.Ordered {
	mods := make([]any, len(p.Mods))
	for index, mod := range p.Mods {
		mods[index] = jsonout.Ordered{
			{Key: "position", Value: mod.SourceIndex},
			{Key: "source_position", Value: mod.SourcePosition},
			{Key: "display_name", Value: mod.DisplayName},
			{Key: "source", Value: mod.Source},
			{Key: "source_registry_id", Value: nullable(mod.RegistryID)},
			{Key: "steam_id", Value: mod.Row.FirstValue("steamId", "remoteSteamId")},
			{Key: "pdx_id", Value: mod.Row.FirstValue("pdxId", "remotePdxId")},
			{Key: "version", Value: mod.Row["version"]},
			{Key: "required_version", Value: mod.Row["requiredVersion"]},
			{Key: "content_path", Value: mod.CloneName},
			{Key: "registry_descriptor", Value: mod.RegistryFilename},
			{Key: "file_count", Value: mod.FileCount},
			{Key: "bytes", Value: mod.ByteCount},
			{Key: "content_sha256", Value: nullable(mod.ContentSHA256)},
			{Key: "launcher_mod_id", Value: nullable(mod.NewModID)},
		}
	}
	return jsonout.Ordered{
		{Key: "format", Value: ManifestFormat},
		{Key: "name", Value: p.SnapshotName},
		{Key: "created_at", Value: p.CreatedAt},
		{Key: "source_playset", Value: jsonout.Ordered{
			{Key: "id", Value: p.SourcePlaysetID},
			{Key: "name", Value: p.SourcePlaysetName},
		}},
		{Key: "registered", Value: registered},
		{Key: "launcher_playset_id", Value: playsetID},
		{Key: "mods", Value: mods},
	}
}

func nullable(value string) any {
	if value == "" {
		return nil
	}
	return value
}

// readme explains to a future reader what the directory is and is not.
func (p *Plan) readme() string {
	lines := []string{
		"Preserved CK3 playset: " + p.SnapshotName,
		"Source playset: " + p.SourcePlaysetName,
		"Created: " + p.CreatedAt,
		"",
		"This is a private, update-proof backup of third-party mod content.",
		"Do not distribute it without permission from every source mod author.",
		"The original playset and installed mods were not modified.",
		"",
		"Enabled contents, in load order:",
	}
	for _, mod := range p.Mods {
		version := mod.Row.String("version")
		if version == "" {
			version = "unknown version"
		}
		lines = append(lines, fmt.Sprintf("%d: %s (%s)", mod.SourceIndex, mod.DisplayName, version))
	}
	return strings.Join(lines, "\n") + "\n"
}
