// Package install derives the Launcher descriptors and the payload sync for
// the repository's local mods.
//
// Planning never writes. The caller decides whether to apply the plan.
package install

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/pdx"
	"codeberg.org/traidare/ck3_mods/internal/plan"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

// Plan is the derived, non-mutating result of inspecting the workspace.
type Plan struct {
	LauncherModDir string
	ModSlugs       []string
	// Files counts payload copies, Descriptors the derived .mod files, and
	// Removals installed files the workspace no longer provides.
	Files       int
	Descriptors int
	Removals    int
	Excluded    []string
	Ops         *plan.Plan
}

// Build derives the Launcher descriptors and a complete sync plan.
func Build(space *workspace.Workspace, launcherModDir string, modSlugs []string) (*Plan, error) {
	destinationRoot := fsutil.MustAbs(launcherModDir)
	sourceRoot, err := filepath.EvalSymlinks(space.ModsDir())
	if err != nil {
		return nil, fmt.Errorf("cannot resolve workspace mods directory: %w", err)
	}
	if _, inside := fsutil.RelativeWithin(sourceRoot, destinationRoot); inside {
		return nil, fmt.Errorf("launcher mod directory must not be inside workspace mods")
	}
	if _, inside := fsutil.RelativeWithin(destinationRoot, sourceRoot); inside {
		return nil, fmt.Errorf("workspace mods must not be inside launcher mod directory")
	}

	mods, err := selectMods(space, modSlugs)
	if err != nil {
		return nil, err
	}
	if len(mods) == 0 {
		return nil, fmt.Errorf("no local mods found below %s", space.ModsDir())
	}

	patterns := space.Settings.InstallExclude
	result := &Plan{
		LauncherModDir: destinationRoot,
		Excluded:       patterns,
		Ops:            &plan.Plan{},
	}
	var removals []string
	var pruneRoots []string

	for _, mod := range mods {
		if !fsutil.IsFile(mod.DescriptorPath) {
			return nil, fmt.Errorf("native descriptor is missing: %s", mod.DescriptorPath)
		}
		destination := filepath.Join(destinationRoot, mod.Slug)

		sourceFiles, err := sourceFiles(mod.Root, patterns)
		if err != nil {
			return nil, err
		}
		installedFiles, err := installedFiles(destination, patterns)
		if err != nil {
			return nil, err
		}

		for _, relative := range sortedKeys(sourceFiles) {
			result.Ops.Add(plan.Op{
				Kind:   plan.Copy,
				Owner:  mod.Slug,
				Source: sourceFiles[relative],
				Path:   filepath.Join(destination, filepath.FromSlash(relative)),
			})
			result.Files++
		}
		for _, relative := range sortedKeys(installedFiles) {
			if _, kept := sourceFiles[relative]; !kept {
				removals = append(removals, installedFiles[relative])
			}
		}

		content, err := pdx.DeriveLauncherDescriptor(mod.DescriptorPath, mod.Slug, "mod/"+mod.Slug)
		if err != nil {
			return nil, err
		}
		info, err := os.Stat(mod.DescriptorPath)
		if err != nil {
			return nil, fmt.Errorf("cannot stat %s: %w", mod.DescriptorPath, err)
		}
		result.Ops.Add(plan.Op{
			Kind:  plan.Write,
			Owner: mod.Slug,
			Path:  filepath.Join(destinationRoot, mod.Slug+".mod"),
			Data:  []byte(content),
			Mode:  info.Mode().Perm(),
		})
		result.Descriptors++
		result.ModSlugs = append(result.ModSlugs, mod.Slug)
		pruneRoots = append(pruneRoots, destination)
	}

	// Removals run after every copy so a file moving between mods is never
	// deleted after it has been written.
	for _, path := range uniqueSorted(removals) {
		result.Ops.Add(plan.Op{Kind: plan.Remove, Path: path})
		result.Removals++
	}
	for _, root := range pruneRoots {
		result.Ops.Add(plan.Op{Kind: plan.PruneDirs, Path: root})
	}
	return result, nil
}

// Apply writes the plan, creating the Launcher mod directory first.
func (p *Plan) Apply() error {
	if err := os.MkdirAll(p.LauncherModDir, 0o755); err != nil {
		return fmt.Errorf("cannot create %s: %w", p.LauncherModDir, err)
	}
	return p.Ops.Apply()
}

func selectMods(space *workspace.Workspace, slugs []string) ([]*workspace.Mod, error) {
	if len(slugs) == 0 {
		return space.Mods()
	}
	mods := make([]*workspace.Mod, 0, len(slugs))
	for _, slug := range slugs {
		mod, err := space.Mod(slug)
		if err != nil {
			return nil, err
		}
		mods = append(mods, mod)
	}
	return mods, nil
}

// sourceFiles maps each shipped relative path to the file that provides it.
// Directory symlinks are copied through, matching the rsync --copy-links
// workflow this replaced.
func sourceFiles(modRoot string, patterns []string) (map[string]string, error) {
	result := map[string]string{}
	err := filepath.WalkDir(modRoot, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if path == modRoot {
			return nil
		}
		relative, err := filepath.Rel(modRoot, path)
		if err != nil {
			return err
		}
		relative = filepath.ToSlash(relative)
		if fsutil.MatchAnyGlob(patterns, relative) {
			if entry.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if entry.IsDir() {
			return nil
		}
		if entry.Type()&os.ModeSymlink != 0 {
			return followSymlink(path, relative, patterns, result)
		}
		if !entry.Type().IsRegular() {
			return fmt.Errorf("refusing to install non-regular file: %s", path)
		}
		result[relative] = path
		return nil
	})
	if err != nil {
		return nil, err
	}
	return result, nil
}

func followSymlink(path, relative string, patterns []string, result map[string]string) error {
	target, err := filepath.EvalSymlinks(path)
	if err != nil {
		return fmt.Errorf("cannot resolve symlink: %s", path)
	}
	info, err := os.Stat(target)
	if err != nil {
		return fmt.Errorf("cannot resolve symlink: %s", path)
	}
	if info.Mode().IsRegular() {
		result[relative] = target
		return nil
	}
	if !info.IsDir() {
		return fmt.Errorf("refusing to install non-regular file: %s", path)
	}
	nested, err := fsutil.WalkFiles(target)
	if err != nil {
		return err
	}
	for _, name := range nested {
		nestedRelative := relative + "/" + name
		if fsutil.MatchAnyGlob(patterns, nestedRelative) {
			continue
		}
		result[nestedRelative] = filepath.Join(target, filepath.FromSlash(name))
	}
	return nil
}

// installedFiles lists what the Launcher mod directory already holds.
func installedFiles(root string, patterns []string) (map[string]string, error) {
	info, err := os.Lstat(root)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]string{}, nil
		}
		return nil, fmt.Errorf("cannot inspect %s: %w", root, err)
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
		return nil, fmt.Errorf("installed mod destination is not a directory: %s", root)
	}
	files, err := fsutil.WalkFiles(root)
	if err != nil {
		return nil, err
	}
	result := make(map[string]string, len(files))
	for _, relative := range files {
		if fsutil.MatchAnyGlob(patterns, relative) {
			continue
		}
		result[relative] = filepath.Join(root, filepath.FromSlash(relative))
	}
	return result, nil
}

func sortedKeys(values map[string]string) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func uniqueSorted(values []string) []string {
	seen := map[string]bool{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		if !seen[value] {
			seen[value] = true
			result = append(result, value)
		}
	}
	sort.Strings(result)
	return result
}

// Summary renders the same four counters the Python command printed.
func (p *Plan) Summary(applied bool) string {
	state := "preview"
	if applied {
		state = "applied"
	}
	var builder strings.Builder
	fmt.Fprintf(&builder, "Install %s\n", state)
	fmt.Fprintf(&builder, "  Mods: %d\n", len(p.ModSlugs))
	fmt.Fprintf(&builder, "  Payload files: %d\n", p.Files)
	fmt.Fprintf(&builder, "  Launcher descriptors: %d\n", p.Descriptors)
	fmt.Fprintf(&builder, "  Removals: %d\n", p.Removals)
	return builder.String()
}

// JSON returns the machine-readable form of the plan.
func (p *Plan) JSON(applied bool) map[string]any {
	state := "preview"
	if applied {
		state = "applied"
	}
	descriptors := make([]map[string]any, 0, p.Descriptors)
	files := make([]map[string]any, 0, p.Files)
	removals := make([]string, 0, p.Removals)
	for _, op := range p.Ops.Ops {
		switch op.Kind {
		case plan.Write:
			descriptors = append(descriptors, map[string]any{
				"modSlug":     op.Owner,
				"destination": op.Path,
			})
		case plan.Copy:
			files = append(files, map[string]any{
				"modSlug":     op.Owner,
				"source":      op.Source,
				"destination": op.Path,
			})
		case plan.Remove:
			removals = append(removals, op.Path)
		}
	}
	excluded := p.Excluded
	if excluded == nil {
		excluded = []string{}
	}
	return map[string]any{
		"state":          state,
		"launcherModDir": p.LauncherModDir,
		"mods":           p.ModSlugs,
		"descriptors":    descriptors,
		"files":          files,
		"removals":       removals,
		"excluded":       excluded,
	}
}
