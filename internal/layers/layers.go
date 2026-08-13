// Package layers resolves portable playset entries into the installed CK3 mod
// roots that make up the effective load order.
//
// Host paths stay inside this package: warnings name mods, never directories.
package layers

import (
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/conflicts"
	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/pdx"
	"codeberg.org/traidare/ck3_mods/internal/playset"
	"codeberg.org/traidare/ck3_mods/internal/report"
)

// Discovery is the resolved load order plus whatever could not be resolved.
type Discovery struct {
	Providers []conflicts.Provider
	Warnings  []report.Warning
	Playset   report.PlaysetRecord
}

// readDescriptor reads a descriptor, keeping host paths out of the message.
func readDescriptor(descriptorPath, label string) (pdx.Descriptor, error) {
	if !fsutil.IsFile(descriptorPath) {
		return pdx.Descriptor{}, fmt.Errorf("%s is missing", label)
	}
	descriptor, err := pdx.Load(descriptorPath)
	if err != nil {
		var readError *pdx.ReadError
		if errors.As(err, &readError) {
			return pdx.Descriptor{}, fmt.Errorf("%s is unreadable", label)
		}
		return pdx.Descriptor{}, fmt.Errorf("%s is invalid: %w", label, err)
	}
	return descriptor, nil
}

// SafeRegistryPath resolves a Launcher registry ID inside CK3_PARADOX_DIR and
// refuses anything that would escape it.
func SafeRegistryPath(paradoxDir, registryID string) (string, error) {
	relative := strings.ReplaceAll(registryID, `\`, "/")
	if relative == "" || strings.HasPrefix(relative, "/") {
		return "", fmt.Errorf("unsafe local registry ID: %q", registryID)
	}
	for _, part := range strings.Split(relative, "/") {
		if part == ".." {
			return "", fmt.Errorf("unsafe local registry ID: %q", registryID)
		}
	}

	root := fsutil.MustAbs(paradoxDir)
	resolved := fsutil.MustAbs(filepath.Join(root, filepath.FromSlash(path.Clean(relative))))
	if _, inside := fsutil.RelativeWithin(root, resolved); !inside {
		return "", fmt.Errorf("local registry ID escapes CK3_PARADOX_DIR: %q", registryID)
	}
	return resolved, nil
}

// payloadPath resolves the mod directory a local Launcher descriptor points at,
// falling back to the conventional mod/<name> location.
func payloadPath(descriptor pdx.Descriptor, paradoxDir string) (string, error) {
	rawPath, err := descriptor.Value("path", "")
	if err != nil {
		return "", err
	}
	if rawPath == "" {
		return "", fmt.Errorf("local Launcher descriptor has no path field")
	}

	candidate := rawPath
	if !filepath.IsAbs(candidate) {
		candidate = filepath.Join(paradoxDir, candidate)
	}
	resolved := fsutil.MustAbs(candidate)
	if fsutil.IsDir(resolved) {
		return resolved, nil
	}
	fallback := fsutil.MustAbs(filepath.Join(paradoxDir, "mod", filepath.Base(rawPath)))
	if fsutil.IsDir(fallback) {
		return fallback, nil
	}
	return "", fmt.Errorf("configured local mod payload is missing")
}

// mergeReplacePaths collects the replace_path declarations of every descriptor
// describing the same mod, since the Launcher and payload copies can differ.
func mergeReplacePaths(descriptors ...pdx.Descriptor) []string {
	unique := map[string]bool{}
	for _, descriptor := range descriptors {
		for _, replacePath := range descriptor.ReplacePaths() {
			normalized := strings.Trim(strings.ReplaceAll(strings.TrimSpace(replacePath), `\`, "/"), "/")
			if normalized != "" {
				unique[normalized] = true
			}
		}
	}
	merged := make([]string, 0, len(unique))
	for value := range unique {
		merged = append(merged, value)
	}
	sort.Strings(merged)
	return merged
}

func workshopProvider(mod playset.Mod, workshopDir string) (conflicts.Provider, error) {
	if mod.SteamID == "" {
		return conflicts.Provider{}, fmt.Errorf("workshop playset entry has no Steam ID")
	}
	root := fsutil.MustAbs(filepath.Join(workshopDir, mod.SteamID))
	descriptor, err := readDescriptor(filepath.Join(root, "descriptor.mod"), "Workshop descriptor.mod")
	if err != nil {
		return conflicts.Provider{}, err
	}

	name := mod.DisplayName
	if descriptor.Has("name") {
		declared, err := descriptor.Name()
		if err != nil {
			return conflicts.Provider{}, err
		}
		name = declared
	}
	return conflicts.NewProvider(mod.StableID(), name, root, mod.Position, "steam",
		mergeReplacePaths(descriptor))
}

func localProvider(mod playset.Mod, paradoxDir string) (conflicts.Provider, error) {
	if mod.GameRegistryID == "" {
		return conflicts.Provider{}, fmt.Errorf("local playset entry has no gameRegistryId")
	}
	registryPath, err := SafeRegistryPath(paradoxDir, mod.GameRegistryID)
	if err != nil {
		return conflicts.Provider{}, err
	}
	launcherDescriptor, err := readDescriptor(registryPath, "local Launcher descriptor")
	if err != nil {
		return conflicts.Provider{}, err
	}
	root, err := payloadPath(launcherDescriptor, paradoxDir)
	if err != nil {
		return conflicts.Provider{}, err
	}

	payloadDescriptor := launcherDescriptor
	payloadDescriptorPath := filepath.Join(root, "descriptor.mod")
	if fsutil.IsFile(payloadDescriptorPath) {
		payloadDescriptor, err = readDescriptor(payloadDescriptorPath, "local payload descriptor.mod")
		if err != nil {
			return conflicts.Provider{}, err
		}
	}

	name := mod.DisplayName
	if payloadDescriptor.Has("name") {
		declared, err := payloadDescriptor.Name()
		if err != nil {
			return conflicts.Provider{}, err
		}
		name = declared
	}
	return conflicts.NewProvider(mod.StableID(), name, root, mod.Position, "local",
		mergeReplacePaths(launcherDescriptor, payloadDescriptor))
}

// Discover resolves a playset's enabled entries into ordered provider roots.
func Discover(source playset.Playset, workshopDir, paradoxDir string) Discovery {
	var providers []conflicts.Provider
	var warnings []report.Warning

	for _, mod := range source.EnabledMods() {
		isLocal := mod.Source == "local" || mod.GameRegistryID != ""

		var provider conflicts.Provider
		var err error
		switch {
		case isLocal:
			provider, err = localProvider(mod, paradoxDir)
		case mod.SteamID != "":
			provider, err = workshopProvider(mod, workshopDir)
		default:
			err = fmt.Errorf("entry has neither a local registry ID nor a Steam ID")
		}
		if err != nil {
			detail := err.Error()
			if os.IsNotExist(err) || os.IsPermission(err) {
				detail = "filesystem access failed while resolving installed content"
			}
			code := "enabled_mod_missing"
			if isLocal {
				code = "enabled_local_mod_missing"
			}
			position := mod.Position
			warnings = append(warnings, report.Warning{
				Code:     code,
				Message:  mod.DisplayName + ": " + detail,
				ModID:    mod.StableID(),
				Position: &position,
			})
			continue
		}
		providers = append(providers, provider)
	}

	sort.SliceStable(providers, func(left, right int) bool {
		if providers[left].Position != providers[right].Position {
			return providers[left].Position < providers[right].Position
		}
		return providers[left].StableID < providers[right].StableID
	})
	conflicts.SortWarnings(warnings)

	return Discovery{
		Providers: providers,
		Warnings:  warnings,
		Playset: report.PlaysetRecord{
			Name:            source.Name,
			Game:            "ck3",
			SelectionSource: source.SelectionSource,
			ModsTotal:       len(source.Mods),
			ModsEnabled:     len(source.EnabledMods()),
		},
	}
}
