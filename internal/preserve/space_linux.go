//go:build linux

package preserve

import (
	"fmt"
	"syscall"
)

// freeBytes reports the space available to this user under path, using the
// fragment size Python's shutil.disk_usage reads.
func freeBytes(path string) (int64, error) {
	var stat syscall.Statfs_t
	if err := syscall.Statfs(path, &stat); err != nil {
		return 0, fmt.Errorf("could not inspect free space under %s: %w", path, err)
	}
	blockSize := int64(stat.Frsize)
	if blockSize == 0 {
		blockSize = int64(stat.Bsize)
	}
	return int64(stat.Bavail) * blockSize, nil
}
