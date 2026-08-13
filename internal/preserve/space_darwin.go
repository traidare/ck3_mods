//go:build darwin

package preserve

import (
	"fmt"
	"syscall"
)

// freeBytes reports the space available to this user under path. macOS reports
// only one block size, so there is no fragment size to prefer.
func freeBytes(path string) (int64, error) {
	var stat syscall.Statfs_t
	if err := syscall.Statfs(path, &stat); err != nil {
		return 0, fmt.Errorf("could not inspect free space under %s: %w", path, err)
	}
	return int64(stat.Bavail) * int64(stat.Bsize), nil
}
