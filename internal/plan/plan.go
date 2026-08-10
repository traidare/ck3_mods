// Package plan carries the mutations a command intends to make.
//
// Every command that writes outside the repository builds a Plan first and
// prints it. Nothing touches the filesystem until Apply is called, which the
// command layer only does for --apply.
package plan

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
)

// Kind names one atomic mutation.
type Kind string

const (
	// Copy replaces Path with the contents of Source.
	Copy Kind = "copy"
	// Write replaces Path with an in-memory payload.
	Write Kind = "write"
	// Remove deletes Path, which must not be a directory.
	Remove Kind = "remove"
	// PruneDirs removes now-empty directories below Path, deepest first.
	PruneDirs Kind = "prune_dirs"
)

// Op is one planned mutation. Only the fields its Kind uses are set.
type Op struct {
	Kind   Kind
	Path   string
	Source string
	Data   []byte
	Mode   os.FileMode
	// Owner names the mod or subject the operation belongs to, for reporting.
	Owner string
}

// Plan is an ordered, inspectable list of mutations.
type Plan struct {
	Ops []Op
}

// Add appends one operation.
func (p *Plan) Add(op Op) { p.Ops = append(p.Ops, op) }

// Count returns how many operations of one kind the plan holds.
func (p *Plan) Count(kind Kind) int {
	total := 0
	for _, op := range p.Ops {
		if op.Kind == kind {
			total++
		}
	}
	return total
}

// Paths returns the sorted destination paths of one kind.
func (p *Plan) Paths(kind Kind) []string {
	var paths []string
	for _, op := range p.Ops {
		if op.Kind == kind {
			paths = append(paths, op.Path)
		}
	}
	sort.Strings(paths)
	return paths
}

// Empty reports whether the plan would change nothing.
func (p *Plan) Empty() bool { return len(p.Ops) == 0 }

// Apply performs every operation in order. It stops at the first failure, so a
// partially applied plan names the operation that broke.
func (p *Plan) Apply() error {
	for _, op := range p.Ops {
		if err := apply(op); err != nil {
			return fmt.Errorf("%s %s: %w", op.Kind, op.Path, err)
		}
	}
	return nil
}

func apply(op Op) error {
	switch op.Kind {
	case Copy:
		return fsutil.CopyFileAtomic(op.Source, op.Path)
	case Write:
		mode := op.Mode
		if mode == 0 {
			mode = 0o644
		}
		return fsutil.WriteFileAtomic(op.Path, op.Data, mode)
	case Remove:
		info, err := os.Lstat(op.Path)
		if err != nil {
			if os.IsNotExist(err) {
				return nil
			}
			return err
		}
		if info.IsDir() {
			return fmt.Errorf("refusing planned directory removal")
		}
		return os.Remove(op.Path)
	case PruneDirs:
		return pruneDirs(op.Path)
	}
	return fmt.Errorf("unknown plan operation %q", op.Kind)
}

// pruneDirs removes empty directories below root, deepest first. A directory
// that still holds content simply fails to be removed, which is not an error.
func pruneDirs(root string) error {
	if !fsutil.IsDir(root) {
		return nil
	}
	var directories []string
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() && path != root {
			directories = append(directories, path)
		}
		return nil
	})
	if err != nil {
		return err
	}
	sort.Sort(sort.Reverse(sort.StringSlice(directories)))
	for _, directory := range directories {
		_ = os.Remove(directory)
	}
	return nil
}
