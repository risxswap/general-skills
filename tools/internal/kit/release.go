package kit

import (
	"archive/zip"
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Release builds offline distributions into a new directory; existing output is preserved.
func Release(root, out, version, targets string) error {
	root, e := filepath.Abs(root)
	if e != nil {
		return e
	}
	out, e = filepath.Abs(out)
	if e != nil {
		return e
	}
	if _, e = os.Lstat(out); !os.IsNotExist(e) {
		return fmt.Errorf("output must not exist: %s", out)
	}
	bundle, e := Build(root, version)
	if e != nil {
		return e
	}
	if e = os.MkdirAll(filepath.Dir(out), 0755); e != nil {
		return e
	}
	work, e := os.MkdirTemp(filepath.Dir(out), ".general-skills-release-")
	if e != nil {
		return e
	}
	defer os.RemoveAll(work)
	seen := map[string]bool{}
	for _, target := range strings.Split(targets, ",") {
		pair := strings.Split(target, "/")
		if len(pair) != 2 || (pair[0] != "darwin" && pair[0] != "linux" && pair[0] != "windows") || (pair[1] != "amd64" && pair[1] != "arm64") || seen[target] {
			return fmt.Errorf("invalid or duplicate target %q", target)
		}
		seen[target] = true
		name := "general-skills"
		if pair[0] == "windows" {
			name += ".exe"
		}
		binary := filepath.Join(work, name)
		cmd := exec.Command("go", "build", "-trimpath", "-ldflags", "-s -w -X main.version="+version, "-o", binary, "./cmd/general-skills")
		cmd.Dir = filepath.Join(root, "tools")
		for _, v := range os.Environ() {
			if !strings.HasPrefix(v, "GOOS=") && !strings.HasPrefix(v, "GOARCH=") && !strings.HasPrefix(v, "CGO_ENABLED=") {
				cmd.Env = append(cmd.Env, v)
			}
		}
		cmd.Env = append(cmd.Env, "CGO_ENABLED=0", "GOOS="+pair[0], "GOARCH="+pair[1])
		if output, err := cmd.CombinedOutput(); err != nil {
			return fmt.Errorf("build %s: %w\n%s", target, err, output)
		}
		executable, e := os.ReadFile(binary)
		if e != nil {
			return e
		}
		if e = os.Remove(binary); e != nil {
			return e
		}
		readme := []byte("General Skills " + version + "\nRun " + name + " with no arguments for interactive installation.\nOffline: keep skills.bundle.zip beside the executable.\nExample: " + name + " install --scenario java --scope project --project-dir /path/to/project\nUse --dry-run to preview; conflicts default to fail.\nProject: <project>/.agents/skills; user: ~/.agents/skills.\n")
		checks := []byte(fmt.Sprintf("%s  %s\n%s  skills.bundle.zip\n%s  README.txt\n", digest(executable), name, digest(bundle), digest(readme)))
		var buf bytes.Buffer
		z := zip.NewWriter(&buf)
		for _, item := range []struct {
			n string
			b []byte
		}{{name, executable}, {"skills.bundle.zip", bundle}, {"README.txt", readme}, {"SHA256SUMS", checks}} {
			mode := os.FileMode(0644)
			if item.n == name {
				mode = 0755
			}
			if e = zipWrite(z, item.n, item.b, mode); e != nil {
				return e
			}
		}
		if e = z.Close(); e != nil {
			return e
		}
		archive := "general-skills-" + version + "-" + pair[0] + "-" + pair[1] + ".zip"
		if e = os.WriteFile(filepath.Join(work, archive), buf.Bytes(), 0644); e != nil {
			return e
		}
		if e = os.WriteFile(filepath.Join(work, archive+".sha256"), []byte(digest(buf.Bytes())+"  "+archive+"\n"), 0644); e != nil {
			return e
		}
	}
	if len(seen) == 0 {
		return fmt.Errorf("no targets")
	}
	return os.Rename(work, out)
}
