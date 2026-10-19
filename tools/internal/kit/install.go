package kit

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Options struct {
	Scenario, Scope, ProjectDir, Conflict string
	DryRun                                bool
}
type Action struct {
	Skill string
	Kind  string
}

func Destination(o Options) (string, error) {
	var base string
	switch o.Scope {
	case "project":
		if strings.TrimSpace(o.ProjectDir) == "" {
			return "", fmt.Errorf("project scope requires --project-dir")
		}
		base = o.ProjectDir
	case "user":
		if o.ProjectDir != "" {
			return "", fmt.Errorf("--project-dir is only valid for project scope")
		}
		var e error
		base, e = os.UserHomeDir()
		if e != nil {
			return "", e
		}
	default:
		return "", fmt.Errorf("scope must be project or user")
	}
	if strings.HasPrefix(base, "~/") {
		home, e := os.UserHomeDir()
		if e != nil {
			return "", e
		}
		base = filepath.Join(home, base[2:])
	}
	base, e := filepath.Abs(base)
	if e != nil {
		return "", e
	}
	base, e = filepath.EvalSymlinks(base)
	if e != nil {
		return "", e
	}
	info, e := os.Stat(base)
	if e != nil {
		return "", e
	}
	if !info.IsDir() {
		return "", fmt.Errorf("not a directory: %s", base)
	}
	return filepath.Join(base, ".agents", "skills"), nil
}

// Existing parents must be real directories, not symlinks to another installation.
func checkParents(dest string) error {
	for p := dest; ; p = filepath.Dir(p) {
		info, e := os.Lstat(p)
		if e == nil {
			if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
				return fmt.Errorf("unsafe installation directory: %s", p)
			}
		} else if !os.IsNotExist(e) {
			return e
		}
		if filepath.Dir(p) == p {
			break
		}
	}
	return nil
}
func Plan(b *Bundle, o Options, dest string) ([]Action, error) {
	if err := b.Validate(); err != nil {
		return nil, err
	}
	names, err := Skills(o.Scenario)
	if err != nil {
		return nil, err
	}
	if o.Conflict != "fail" && o.Conflict != "skip" && o.Conflict != "replace" {
		return nil, fmt.Errorf("conflict must be fail, skip or replace")
	}
	if err = checkParents(dest); err != nil {
		return nil, err
	}
	var result []Action
	for _, n := range names {
		a := Action{n, "add"}
		info, e := os.Lstat(filepath.Join(dest, n))
		if e == nil {
			if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
				return nil, fmt.Errorf("refusing non-directory skill: %s", n)
			}
			switch o.Conflict {
			case "fail":
				return nil, fmt.Errorf("skill already exists: %s (choose --conflict skip or replace)", n)
			case "skip":
				if _, e = os.Stat(filepath.Join(dest, n, "SKILL.md")); e != nil {
					return nil, fmt.Errorf("cannot skip incomplete skill %s", n)
				}
				a.Kind = "skip"
			case "replace":
				a.Kind = "replace"
			}
		} else if !os.IsNotExist(e) {
			return nil, e
		}
		result = append(result, a)
	}
	return result, nil
}
func Install(b *Bundle, o Options, dest string) ([]Action, error) {
	return install(b, o, dest, os.Rename)
}
func install(b *Bundle, o Options, dest string, rename func(string, string) error) ([]Action, error) {
	actions, e := Plan(b, o, dest)
	if e != nil || o.DryRun {
		return actions, e
	}
	if e = os.MkdirAll(dest, 0755); e != nil {
		return nil, e
	}
	lock := filepath.Join(filepath.Dir(dest), ".general-skills-install.lock")
	if e = os.Mkdir(lock, 0700); e != nil {
		return nil, fmt.Errorf("installation lock %s: %w", lock, e)
	}
	defer os.Remove(lock)
	actions, e = Plan(b, o, dest)
	if e != nil {
		return nil, e
	}
	stage, e := os.MkdirTemp(filepath.Dir(dest), ".general-skills-stage-")
	if e != nil {
		return nil, e
	}
	defer os.RemoveAll(stage)
	backup, e := os.MkdirTemp(filepath.Dir(dest), ".general-skills-backup-")
	if e != nil {
		return nil, e
	}
	keepBackup := false
	defer func() {
		if !keepBackup {
			_ = os.RemoveAll(backup)
		}
	}()
	for _, a := range actions {
		if a.Kind == "skip" {
			continue
		}
		for _, k := range sortedKeys(b.Files) {
			if !strings.HasPrefix(k, a.Skill+"/") {
				continue
			}
			p := filepath.Join(stage, filepath.FromSlash(k))
			if e = os.MkdirAll(filepath.Dir(p), 0755); e != nil {
				return nil, e
			}
			if e = os.WriteFile(p, b.Files[k], 0644); e != nil {
				return nil, e
			}
		}
	}
	var applied, saved []string
	rollback := func(cause error) error {
		var errs []error
		errs = append(errs, cause)
		for i := len(applied) - 1; i >= 0; i-- {
			if err := os.RemoveAll(filepath.Join(dest, applied[i])); err != nil {
				errs = append(errs, err)
			}
		}
		for i := len(saved) - 1; i >= 0; i-- {
			n := saved[i]
			if err := rename(filepath.Join(backup, n), filepath.Join(dest, n)); err != nil {
				keepBackup = true
				errs = append(errs, fmt.Errorf("restore failed; backup retained at %s: %w", backup, err))
			}
		}
		return errors.Join(errs...)
	}
	for _, a := range actions {
		if a.Kind == "skip" {
			continue
		}
		to := filepath.Join(dest, a.Skill)
		if a.Kind == "replace" {
			if e = rename(to, filepath.Join(backup, a.Skill)); e != nil {
				return nil, rollback(e)
			}
			saved = append(saved, a.Skill)
		} else if _, e = os.Lstat(to); !os.IsNotExist(e) {
			return nil, rollback(fmt.Errorf("destination changed: %s", to))
		}
		if e = rename(filepath.Join(stage, a.Skill), to); e != nil {
			return nil, rollback(e)
		}
		applied = append(applied, a.Skill)
	}
	return actions, nil
}
