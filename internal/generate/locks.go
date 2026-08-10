package generate

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

// SourceLockName is the per-mod record of reviewed upstream source hashes.
const SourceLockName = "source-lock.json"

// SourceLockSchemaVersion is the only lock schema this tool reads.
const SourceLockSchemaVersion = 1

// SourceLockPath is where one mod keeps its accepted source hashes.
func SourceLockPath(mod *workspace.Mod) string {
	return filepath.Join(mod.ToolingRoot, SourceLockName)
}

type sourceLockFile struct {
	SchemaVersion *int `json:"schemaVersion"`
	Sources       map[string]struct {
		Sha256 string `json:"sha256"`
	} `json:"sources"`
}

// LoadSourceLocks reads the accepted hashes for one mod, if it records any.
func LoadSourceLocks(mod *workspace.Mod) (map[string]string, error) {
	path := SourceLockPath(mod)
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]string{}, nil
		}
		return nil, errorf("invalid source lock %s: %v", path, err)
	}
	var file sourceLockFile
	if err := json.Unmarshal(data, &file); err != nil {
		return nil, errorf("invalid source lock %s: %v", path, err)
	}
	if file.SchemaVersion != nil && *file.SchemaVersion != SourceLockSchemaVersion {
		return nil, errorf("unsupported source lock schema: %s", path)
	}
	accepted := map[string]string{}
	for name, record := range file.Sources {
		digest := strings.ToLower(record.Sha256)
		if len(digest) != 64 || strings.Trim(digest, "0123456789abcdef") != "" {
			return nil, errorf("invalid SHA-256 for source %q in %s", name, path)
		}
		accepted[name] = digest
	}
	return accepted, nil
}

// VerifySourceLocks fails when a locked source no longer hashes as reviewed.
//
// A mod without a lock file has nothing to verify: locks are opt-in, and the
// ones that exist guard generators whose upstream must be reviewed by hand.
func VerifySourceLocks(mod *workspace.Mod, sources map[string]string) error {
	if !fsutil.IsFile(SourceLockPath(mod)) {
		return nil
	}
	accepted, err := LoadSourceLocks(mod)
	if err != nil {
		return err
	}
	current, err := hashSources(sources)
	if err != nil {
		return err
	}

	var unknown, unlocked, mismatched []string
	for name := range accepted {
		if _, present := current[name]; !present {
			unknown = append(unknown, name)
		}
	}
	for name := range current {
		if _, present := accepted[name]; !present {
			unlocked = append(unlocked, name)
		}
	}
	for name, digest := range accepted {
		if other, present := current[name]; present && other != digest {
			mismatched = append(mismatched, name)
		}
	}
	sort.Strings(unknown)
	sort.Strings(unlocked)
	sort.Strings(mismatched)

	var details []string
	if len(unknown) > 0 {
		details = append(details, "unknown locked sources: "+strings.Join(unknown, ", "))
	}
	if len(unlocked) > 0 {
		details = append(details, "unlocked sources: "+strings.Join(unlocked, ", "))
	}
	if len(mismatched) > 0 {
		details = append(details, "changed sources: "+strings.Join(mismatched, ", "))
	}
	if len(details) > 0 {
		return errorf("%s", strings.Join(details, "; "))
	}
	return nil
}

// RenderSourceLocks returns the lock document for the sources as they are now.
func RenderSourceLocks(sources map[string]string) (string, error) {
	current, err := hashSources(sources)
	if err != nil {
		return "", err
	}
	document := map[string]any{
		"schemaVersion": SourceLockSchemaVersion,
		"sources":       map[string]any{},
	}
	entries := document["sources"].(map[string]any)
	for name, digest := range current {
		entries[name] = map[string]string{"sha256": digest}
	}
	encoded, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		return "", err
	}
	return string(encoded) + "\n", nil
}

// WriteSourceLocks records the current hashes for one mod.
func WriteSourceLocks(mod *workspace.Mod, sources map[string]string) (string, error) {
	content, err := RenderSourceLocks(sources)
	if err != nil {
		return "", err
	}
	if err := fsutil.WriteFileAtomic(SourceLockPath(mod), []byte(content), 0o644); err != nil {
		return "", err
	}
	return content, nil
}

func hashSources(sources map[string]string) (map[string]string, error) {
	hashed := make(map[string]string, len(sources))
	for name, path := range sources {
		digest, err := hashSource(path)
		if err != nil {
			return nil, err
		}
		hashed[name] = digest
	}
	return hashed, nil
}

// hashSource digests one file, or a whole tree by its sorted relative paths.
func hashSource(path string) (string, error) {
	info, err := os.Stat(path)
	if err != nil {
		return "", errorf("cannot hash missing source: %s", path)
	}
	if info.Mode().IsRegular() {
		return fsutil.Sha256File(path)
	}
	if !info.IsDir() {
		return "", errorf("cannot hash missing source: %s", path)
	}

	relatives, err := fsutil.WalkFiles(path)
	if err != nil {
		return "", err
	}
	digest := sha256.New()
	length := make([]byte, 8)
	for _, relative := range relatives {
		binary.BigEndian.PutUint64(length, uint64(len(relative)))
		digest.Write(length)
		digest.Write([]byte(relative))
		file, err := os.Open(filepath.Join(path, filepath.FromSlash(relative)))
		if err != nil {
			return "", err
		}
		_, err = io.Copy(digest, file)
		file.Close()
		if err != nil {
			return "", err
		}
	}
	return hex.EncodeToString(digest.Sum(nil)), nil
}
