// Package fsutil holds the filesystem primitives shared by every command:
// tree walking, content digests, and atomic writes.
package fsutil

import (
	"crypto/sha256"
	"encoding/hex"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
)

// HiddenSkipped reports whether any component of a slash-separated relative
// path starts with a dot. CK3 never loads such files, and the repository keeps
// its own metadata there.
func HiddenSkipped(relative string) bool {
	for _, part := range strings.Split(relative, "/") {
		if strings.HasPrefix(part, ".") {
			return true
		}
	}
	return false
}

// WalkFiles returns every regular file under root as a slash-separated path
// relative to root, sorted. Symlinked directories are not followed, matching
// pathlib.Path.rglob.
func WalkFiles(root string) ([]string, error) {
	var files []string
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			return nil
		}
		relative, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		relative = filepath.ToSlash(relative)
		if !entry.Type().IsRegular() {
			// Resolve symlinks the way Path.is_file() does.
			info, statErr := os.Stat(path)
			if statErr != nil || !info.Mode().IsRegular() {
				return nil
			}
		}
		files = append(files, relative)
		return nil
	})
	if err != nil {
		return nil, err
	}
	sort.Strings(files)
	return files, nil
}

// Sha256File returns the streaming SHA-256 digest of one file.
func Sha256File(path string) (string, error) {
	handle, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer handle.Close()

	digest := sha256.New()
	if _, err := io.Copy(digest, handle); err != nil {
		return "", err
	}
	return hex.EncodeToString(digest.Sum(nil)), nil
}

// Sha256Bytes returns the digest of an in-memory payload.
func Sha256Bytes(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

// HashResult carries one job's digest or the error that prevented it.
type HashResult struct {
	Path   string
	Sha256 string
	Err    error
}

// HashFiles digests many files in parallel. Results are returned in the order
// the paths were given, so callers stay deterministic.
func HashFiles(paths []string) []HashResult {
	results := make([]HashResult, len(paths))
	workers := runtime.GOMAXPROCS(0)
	if workers > len(paths) {
		workers = len(paths)
	}
	if workers < 1 {
		return results
	}

	jobs := make(chan int)
	var group sync.WaitGroup
	for range workers {
		group.Add(1)
		go func() {
			defer group.Done()
			for index := range jobs {
				digest, err := Sha256File(paths[index])
				results[index] = HashResult{Path: paths[index], Sha256: digest, Err: err}
			}
		}()
	}
	for index := range paths {
		jobs <- index
	}
	close(jobs)
	group.Wait()
	return results
}

// WriteFileAtomic replaces destination in one rename, creating parents first.
func WriteFileAtomic(destination string, data []byte, mode os.FileMode) error {
	directory := filepath.Dir(destination)
	if err := os.MkdirAll(directory, 0o755); err != nil {
		return err
	}
	temporary, err := os.CreateTemp(directory, "."+filepath.Base(destination)+".")
	if err != nil {
		return err
	}
	name := temporary.Name()
	defer os.Remove(name)

	if _, err := temporary.Write(data); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Sync(); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Close(); err != nil {
		return err
	}
	if err := os.Chmod(name, mode); err != nil {
		return err
	}
	return os.Rename(name, destination)
}

// CopyFileAtomic copies source over destination, preserving its mode.
func CopyFileAtomic(source, destination string) error {
	info, err := os.Stat(source)
	if err != nil {
		return err
	}
	data, err := os.ReadFile(source)
	if err != nil {
		return err
	}
	return WriteFileAtomic(destination, data, info.Mode().Perm())
}

// SameContent reports whether two files hold identical bytes.
func SameContent(left, right string) (bool, error) {
	leftInfo, err := os.Stat(left)
	if err != nil {
		return false, err
	}
	rightInfo, err := os.Stat(right)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, err
	}
	if leftInfo.Size() != rightInfo.Size() {
		return false, nil
	}
	leftDigest, err := Sha256File(left)
	if err != nil {
		return false, err
	}
	rightDigest, err := Sha256File(right)
	if err != nil {
		return false, err
	}
	return leftDigest == rightDigest, nil
}

// IsDir reports whether path exists and is a directory.
func IsDir(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

// IsFile reports whether path exists and resolves to a regular file.
func IsFile(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.Mode().IsRegular()
}

// ReadTextBOM reads a UTF-8 file, tolerating the byte-order mark that Paradox
// tooling sometimes writes. It mirrors Python's "utf-8-sig" codec.
func ReadTextBOM(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return string(TrimBOM(data)), nil
}

// TrimBOM removes a leading UTF-8 byte-order mark.
func TrimBOM(data []byte) []byte {
	return []byte(strings.TrimPrefix(string(data), "\ufeff"))
}

// RelativeWithin returns the slash-separated path of target inside root and
// reports whether target actually stays inside it.
func RelativeWithin(root, target string) (string, bool) {
	relative, err := filepath.Rel(root, target)
	if err != nil {
		return "", false
	}
	relative = filepath.ToSlash(relative)
	if relative == ".." || strings.HasPrefix(relative, "../") {
		return "", false
	}
	return relative, true
}

// MustAbs resolves path against the working directory without requiring it to
// exist, so error messages can still name it.
func MustAbs(path string) string {
	absolute, err := filepath.Abs(path)
	if err != nil {
		return path
	}
	return absolute
}
