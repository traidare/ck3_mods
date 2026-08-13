package launcher

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"time"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
)

// NewUUID returns a random RFC 4122 version 4 identifier, the form the
// Launcher uses for playset and mod primary keys.
func NewUUID() string {
	var bytes [16]byte
	if _, err := rand.Read(bytes[:]); err != nil {
		// crypto/rand does not fail on any supported platform; a timestamp
		// still yields a unique key if it ever does.
		return fmt.Sprintf("%016x-ck3mm", time.Now().UnixNano())
	}
	bytes[6] = (bytes[6] & 0x0f) | 0x40
	bytes[8] = (bytes[8] & 0x3f) | 0x80

	encoded := hex.EncodeToString(bytes[:])
	return encoded[0:8] + "-" + encoded[8:12] + "-" + encoded[12:16] + "-" +
		encoded[16:20] + "-" + encoded[20:32]
}

// Backup copies the Launcher database beside itself before a write. The copy
// is taken with the source open read-only so a running Launcher cannot leave
// it half-written.
func Backup(databasePath string) (string, error) {
	timestamp := time.Now().UTC().Format("20060102T150405.000000")
	timestamp = timestamp[:15] + timestamp[16:] + "Z"
	backupPath := databasePath + ".ck3mm-" + timestamp + ".bak"
	if err := BackupTo(databasePath, backupPath); err != nil {
		return "", err
	}
	return backupPath, nil
}

// BackupTo copies the Launcher database to an explicit destination, for
// callers that name their backups after the operation taking them.
func BackupTo(databasePath, backupPath string) error {
	source, err := Open(databasePath, true)
	if err != nil {
		return err
	}
	defer source.Close()

	if _, err := source.Handle().Exec("VACUUM INTO ?", backupPath); err != nil {
		os.Remove(backupPath)
		return fmt.Errorf("cannot back up the launcher database: %w", err)
	}
	if !fsutil.IsFile(backupPath) {
		return fmt.Errorf("launcher database backup was not created: %s", backupPath)
	}
	return nil
}
