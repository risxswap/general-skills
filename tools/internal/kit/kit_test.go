package kit

import (
	"archive/zip"
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func realTemp(t *testing.T) string {
	t.Helper()
	p, e := filepath.EvalSymlinks(t.TempDir())
	if e != nil {
		t.Fatal(e)
	}
	return p
}
func fixture(t *testing.T) *Bundle {
	t.Helper()
	data, e := Build("../../..", "0.1.0")
	if e != nil {
		t.Fatal(e)
	}
	b, e := Read(data)
	if e != nil {
		t.Fatal(e)
	}
	return b
}
func exists(p string) bool { _, e := os.Stat(p); return e == nil }
func TestScenarioContents(t *testing.T) {
	want := map[string][]string{
		"general":   {"code-review", "development-workflow", "diagnosing-bugs", "humanizer-zh"},
		"java":      {"api-testing", "code-review", "development-workflow", "diagnosing-bugs", "humanizer-zh", "java-backend", "testing-workflow", "ui-testing"},
		"frontend":  {"api-testing", "code-review", "development-workflow", "diagnosing-bugs", "frontend-development", "humanizer-zh", "testing-workflow", "ui-testing"},
		"fullstack": {"api-testing", "code-review", "development-workflow", "diagnosing-bugs", "frontend-development", "humanizer-zh", "java-backend", "testing-workflow", "ui-testing"},
		"testing":   {"api-testing", "testing-workflow", "ui-testing"},
	}
	if len(ScenarioNames) != len(want) {
		t.Fatalf("unexpected scenarios: %v", ScenarioNames)
	}
	for _, scenario := range ScenarioNames {
		got, err := Skills(scenario)
		if err != nil || !reflect.DeepEqual(got, want[scenario]) {
			t.Fatalf("%s: got %v, want %v, error %v", scenario, got, want[scenario], err)
		}
	}
}

func TestScenariosAndOfflineInstall(t *testing.T) {
	b := fixture(t)
	for _, s := range ScenarioNames {
		t.Run(s, func(t *testing.T) {
			project := realTemp(t)
			o := Options{Scenario: s, Scope: "project", ProjectDir: project, Conflict: "fail"}
			dest, e := Destination(o)
			if e != nil {
				t.Fatal(e)
			}
			actions, e := Install(b, o, dest)
			if e != nil {
				t.Fatal(e)
			}
			names, _ := Skills(s)
			if len(actions) != len(names) {
				t.Fatal(actions)
			}
			all, _ := Skills("fullstack")
			for _, n := range all {
				want := false
				for _, x := range names {
					if x == n {
						want = true
					}
				}
				if exists(filepath.Join(dest, n, "SKILL.md")) != want {
					t.Fatal(n)
				}
			}
			for _, a := range actions {
				for k, v := range b.Files {
					if strings.HasPrefix(k, a.Skill+"/") {
						actual, e := os.ReadFile(filepath.Join(dest, filepath.FromSlash(k)))
						if e != nil || !bytes.Equal(actual, v) {
							t.Fatalf("file not preserved: %s %v", k, e)
						}
					}
				}
			}
		})
	}
}
func TestConflictsAndDryRun(t *testing.T) {
	b := fixture(t)
	dest := filepath.Join(realTemp(t), ".agents", "skills")
	o := Options{Scenario: "java", Conflict: "fail", DryRun: true}
	if _, e := Install(b, o, dest); e != nil {
		t.Fatal(e)
	}
	if exists(dest) {
		t.Fatal("dry run wrote files")
	}
	o.DryRun = false
	if _, e := Install(b, o, dest); e != nil {
		t.Fatal(e)
	}
	p := filepath.Join(dest, "java-backend", "local.txt")
	os.WriteFile(p, []byte("custom"), 0600)
	if _, e := Install(b, o, dest); e == nil {
		t.Fatal("conflict accepted")
	}
	if !exists(p) {
		t.Fatal("lost custom file")
	}
	o.Conflict = "skip"
	actions, e := Install(b, o, dest)
	if e != nil {
		t.Fatal(e)
	}
	for _, a := range actions {
		if a.Kind != "skip" {
			t.Fatal(actions)
		}
	}
	if !exists(p) {
		t.Fatal("skip modified files")
	}
	o.Conflict = "replace"
	if _, e = Install(b, o, dest); e != nil {
		t.Fatal(e)
	}
	if exists(p) {
		t.Fatal("stale file retained")
	}
}
func TestRollbackOnCommitFailure(t *testing.T) {
	b := fixture(t)
	dest := filepath.Join(realTemp(t), ".agents", "skills")
	o := Options{Scenario: "general", Conflict: "fail"}
	if _, e := Install(b, o, dest); e != nil {
		t.Fatal(e)
	}
	marker := filepath.Join(dest, "code-review", "custom.txt")
	os.WriteFile(marker, []byte("keep"), 0600)
	o.Conflict = "replace"
	count := 0
	rename := func(a, c string) error {
		count++
		if count == 4 {
			return errors.New("injected rename failure")
		}
		return os.Rename(a, c)
	}
	if _, e := install(b, o, dest, rename); e == nil {
		t.Fatal("expected failure")
	}
	if !exists(marker) {
		t.Fatal("original not restored")
	}
	names, _ := Skills("general")
	for _, n := range names {
		v, e := os.ReadFile(filepath.Join(dest, n, "SKILL.md"))
		if e != nil || !bytes.Equal(v, b.Files[n+"/SKILL.md"]) {
			t.Fatal("rollback failed", n, e)
		}
	}
}
func TestRejectedTargetsAndLock(t *testing.T) {
	b := fixture(t)
	base := realTemp(t)
	dest := filepath.Join(base, ".agents", "skills")
	os.MkdirAll(dest, 0755)
	os.WriteFile(filepath.Join(dest, "code-review"), []byte("user file"), 0600)
	if _, e := Install(b, Options{Scenario: "general", Conflict: "replace"}, dest); e == nil {
		t.Fatal("file conflict accepted")
	}
	if exists(filepath.Join(dest, "development-workflow")) {
		t.Fatal("partial installation")
	}
	os.Remove(filepath.Join(dest, "code-review"))
	os.Mkdir(filepath.Join(base, ".agents", ".general-skills-install.lock"), 0700)
	if _, e := Install(b, Options{Scenario: "general", Conflict: "fail"}, dest); e == nil {
		t.Fatal("lock ignored")
	}
}
func TestSymlinkProtection(t *testing.T) {
	b := fixture(t)
	base := realTemp(t)
	outside := realTemp(t)
	if e := os.Symlink(outside, filepath.Join(base, ".agents")); e != nil {
		t.Skip(e)
	}
	if _, e := Install(b, Options{Scenario: "general", Conflict: "fail"}, filepath.Join(base, ".agents", "skills")); e == nil {
		t.Fatal("symlink accepted")
	}
	entries, _ := os.ReadDir(outside)
	if len(entries) != 0 {
		t.Fatal("wrote outside")
	}
}
func TestDestinations(t *testing.T) {
	home := realTemp(t)
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)
	got, e := Destination(Options{Scope: "user"})
	if e != nil || got != filepath.Join(home, ".agents", "skills") {
		t.Fatal(got, e)
	}
	for _, o := range []Options{{Scope: "project"}, {Scope: "unknown"}, {Scope: "user", ProjectDir: home}, {Scope: "project", ProjectDir: filepath.Join(home, "missing")}} {
		if _, e := Destination(o); e == nil {
			t.Fatal(o)
		}
	}
}
func TestArchiveValidation(t *testing.T) {
	b := fixture(t)
	b.Files["java-backend/SKILL.md"] = []byte("tampered")
	if e := b.Validate(); e == nil {
		t.Fatal("checksum not checked")
	}
	for _, name := range []string{"../escape", "skills/../escape", "/absolute", "skills/java-backend/CON.txt", "skills\\escape", "manifest.json", "skills/java-backend/SKILL.md"} {
		t.Run(name, func(t *testing.T) {
			var buf bytes.Buffer
			z := zip.NewWriter(&buf)
			zipWrite(z, name, []byte("bad"), 0644)
			if name == "manifest.json" {
				zipWrite(z, name, []byte("again"), 0644)
			}
			z.Close()
			if _, e := Read(buf.Bytes()); e == nil {
				t.Fatal("malformed bundle accepted")
			}
		})
	}
}
func TestScenarioDependencies(t *testing.T) {
	b := fixture(t)
	k := "development-workflow/SKILL.md"
	b.Files[k] = append(b.Files[k], []byte("\n[required Vue](../frontend-development/SKILL.md)\n")...)
	b.Manifest.Files[k] = digest(b.Files[k])
	if e := b.Validate(); e == nil {
		t.Fatal("partial scenario broken link accepted")
	}
}
func TestDeterministicBundle(t *testing.T) {
	a, e := Build("../../..", "1.2.3")
	if e != nil {
		t.Fatal(e)
	}
	b, e := Build("../../..", "1.2.3")
	if e != nil || !reflect.DeepEqual(a, b) {
		t.Fatal("not deterministic", e)
	}
}

func TestFrontendScenarioMembership(t *testing.T) {
	for _, scenario := range []string{"frontend", "fullstack"} {
		names, err := Skills(scenario)
		if err != nil {
			t.Fatal(err)
		}
		found := false
		for _, name := range names {
			if name == "frontend-development" {
				found = true
			}
			if name == "vue-frontend" {
				t.Fatal("obsolete skill in scenario")
			}
		}
		if !found {
			t.Fatalf("%s missing frontend skill", scenario)
		}
	}
	if _, err := Skills("vue"); err == nil {
		t.Fatal("obsolete scenario should not silently select a new bundle")
	}
}
