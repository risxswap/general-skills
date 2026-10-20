package main

import (
	"bytes"
	"general-skills/tools/internal/kit"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCLIInstallPreviewAndError(t *testing.T) {
	data, e := kit.Build("../../..", "0.1.0")
	if e != nil {
		t.Fatal(e)
	}
	dir := t.TempDir()
	bundle := filepath.Join(dir, "bundle.zip")
	os.WriteFile(bundle, data, 0600)
	args := []string{"install", "--scenario", "frontend", "--scope", "project", "--project-dir", dir, "--bundle", bundle, "--dry-run"}
	var out bytes.Buffer
	if e = run(args, strings.NewReader(""), &out); e != nil {
		t.Fatal(e)
	}
	if !strings.Contains(out.String(), "未写入") {
		t.Fatal(out.String())
	}
	if _, e = os.Stat(filepath.Join(dir, ".agents")); !os.IsNotExist(e) {
		t.Fatal("preview wrote files")
	}
	args = args[:len(args)-1]
	if e = run(args, strings.NewReader(""), &out); e != nil {
		t.Fatal(e)
	}
	if e = run(args, strings.NewReader(""), &out); e == nil {
		t.Fatal("default conflict did not fail")
	}
	if e = run([]string{"install", "--scenario", "java"}, strings.NewReader(""), &out); e == nil {
		t.Fatal("missing scope accepted")
	}
}
func TestInteractiveRejectsInvalidAndEOF(t *testing.T) {
	for _, input := range []string{"", "6\n", "1\n3\n", "1\n1\n\n"} {
		var out bytes.Buffer
		if e := run(nil, strings.NewReader(input), &out); e == nil {
			t.Fatalf("accepted %q", input)
		}
	}
}

func TestInteractiveTestingScenario(t *testing.T) {
	data, err := kit.Build("../../..", "0.1.0")
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	bundle := filepath.Join(dir, "bundle.zip")
	if err = os.WriteFile(bundle, data, 0600); err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	if err = run(nil, strings.NewReader("5\n"), &out); err == nil || !strings.Contains(out.String(), "范围 1=项目级") {
		t.Fatalf("testing selection did not reach scope prompt: %v %s", err, out.String())
	}
	if err = run([]string{"install", "--scenario", "testing", "--scope", "project", "--project-dir", dir, "--bundle", bundle}, strings.NewReader(""), &out); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out.String(), "5. 专项测试 (testing)") {
		t.Fatal(out.String())
	}
	entries, err := os.ReadDir(filepath.Join(dir, ".agents", "skills"))
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, entry := range entries {
		names = append(names, entry.Name())
	}
	if strings.Join(names, ",") != "api-testing,testing-workflow,ui-testing" {
		t.Fatalf("unexpected installed skills: %v", names)
	}
}
