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
	for _, input := range []string{"", "5\n", "1\n3\n", "1\n1\n\n"} {
		var out bytes.Buffer
		if e := run(nil, strings.NewReader(input), &out); e == nil {
			t.Fatalf("accepted %q", input)
		}
	}
}
