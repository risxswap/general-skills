package kit

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

var Common = []string{"development-workflow", "diagnosing-bugs", "code-review", "humanizer-zh"}
var Testing = []string{"testing-workflow", "api-testing", "ui-testing"}
var ScenarioNames = []string{"general", "java", "frontend", "fullstack", "testing"}

func Skills(s string) ([]string, error) {
	result := append([]string{}, Common...)
	switch s {
	case "general":
	case "java":
		result = append(result, Testing...)
		result = append(result, "java-backend")
	case "frontend":
		result = append(result, Testing...)
		result = append(result, "frontend-development")
	case "fullstack":
		result = append(result, Testing...)
		result = append(result, "java-backend", "frontend-development")
	case "testing":
		result = append([]string{}, Testing...)
	default:
		return nil, fmt.Errorf("unknown scenario %q", s)
	}
	sort.Strings(result)
	return result, nil
}

type Manifest struct {
	Format  int               `json:"format"`
	Version string            `json:"version"`
	Files   map[string]string `json:"files"`
}
type Bundle struct {
	Manifest Manifest
	Files    map[string][]byte
}

func digest(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }

var safePart = regexp.MustCompile(`^[A-Za-z0-9_.-]+$`)

func safeName(n string) bool {
	if n == "" || path.Clean(n) != n || strings.HasPrefix(n, "/") {
		return false
	}
	for _, p := range strings.Split(n, "/") {
		if !safePart.MatchString(p) || p == "." || p == ".." || strings.HasSuffix(p, ".") {
			return false
		}
		base := strings.ToUpper(strings.SplitN(p, ".", 2)[0])
		if base == "CON" || base == "PRN" || base == "AUX" || base == "NUL" || regexp.MustCompile(`^(COM|LPT)[1-9]$`).MatchString(base) {
			return false
		}
	}
	return true
}

const maxFile = 8 << 20
const maxTotal = 64 << 20

func Build(root, version string) ([]byte, error) {
	if !regexp.MustCompile(`^[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?$`).MatchString(version) {
		return nil, fmt.Errorf("invalid version %q", version)
	}
	b := Bundle{Manifest: Manifest{Format: 1, Version: version, Files: map[string]string{}}, Files: map[string][]byte{}}
	names, _ := Skills("fullstack")
	for _, name := range names {
		dir := filepath.Join(root, "skills", name)
		e := filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if d.Type()&os.ModeSymlink != 0 {
				return fmt.Errorf("symlink not allowed: %s", p)
			}
			if d.IsDir() {
				return nil
			}
			if !d.Type().IsRegular() {
				return fmt.Errorf("not regular: %s", p)
			}
			rel, err := filepath.Rel(filepath.Join(root, "skills"), p)
			if err != nil {
				return err
			}
			rel = filepath.ToSlash(rel)
			if !safeName(rel) {
				return fmt.Errorf("unsupported filename %s", rel)
			}
			info, err := d.Info()
			if err != nil {
				return err
			}
			if info.Size() > maxFile {
				return fmt.Errorf("file too large: %s", rel)
			}
			data, err := os.ReadFile(p)
			if err != nil {
				return err
			}
			b.Files[rel] = data
			b.Manifest.Files[rel] = digest(data)
			return nil
		})
		if e != nil {
			return nil, e
		}
	}
	if err := b.Validate(); err != nil {
		return nil, err
	}
	var out bytes.Buffer
	z := zip.NewWriter(&out)
	manifest, err := json.MarshalIndent(b.Manifest, "", "  ")
	if err != nil {
		return nil, err
	}
	if err = zipWrite(z, "manifest.json", manifest, 0644); err != nil {
		return nil, err
	}
	keys := sortedKeys(b.Files)
	for _, k := range keys {
		if err = zipWrite(z, "skills/"+k, b.Files[k], 0644); err != nil {
			return nil, err
		}
	}
	if err = z.Close(); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}
func zipWrite(z *zip.Writer, n string, data []byte, mode fs.FileMode) error {
	h := &zip.FileHeader{Name: n, Method: zip.Deflate}
	h.SetMode(mode)
	w, e := z.CreateHeader(h)
	if e != nil {
		return e
	}
	_, e = w.Write(data)
	return e
}
func sortedKeys[V any](m map[string]V) []string {
	r := make([]string, 0, len(m))
	for k := range m {
		r = append(r, k)
	}
	sort.Strings(r)
	return r
}
func Read(data []byte) (*Bundle, error) {
	if len(data) > maxTotal {
		return nil, fmt.Errorf("archive too large")
	}
	z, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return nil, err
	}
	b := &Bundle{Files: map[string][]byte{}}
	seen := map[string]bool{}
	total := 0
	for _, f := range z.File {
		if !safeName(f.Name) || !f.Mode().IsRegular() {
			return nil, fmt.Errorf("unsafe archive member %s", f.Name)
		}
		folded := strings.ToLower(f.Name)
		if seen[folded] {
			return nil, fmt.Errorf("duplicate member %s", f.Name)
		}
		seen[folded] = true
		if f.UncompressedSize64 > maxFile {
			return nil, fmt.Errorf("member too large")
		}
		r, e := f.Open()
		if e != nil {
			return nil, e
		}
		v, e := io.ReadAll(io.LimitReader(r, maxFile+1))
		ce := r.Close()
		if e != nil {
			return nil, e
		}
		if ce != nil {
			return nil, ce
		}
		total += len(v)
		if len(v) > maxFile || total > maxTotal {
			return nil, fmt.Errorf("expanded archive too large")
		}
		if f.Name == "manifest.json" {
			if e = json.Unmarshal(v, &b.Manifest); e != nil {
				return nil, e
			}
		} else if strings.HasPrefix(f.Name, "skills/") {
			b.Files[strings.TrimPrefix(f.Name, "skills/")] = v
		} else {
			return nil, fmt.Errorf("unexpected member %s", f.Name)
		}
	}
	if err = b.Validate(); err != nil {
		return nil, err
	}
	return b, nil
}
func (b *Bundle) Validate() error {
	if b.Manifest.Format != 1 || b.Manifest.Version == "" || len(b.Manifest.Files) != len(b.Files) {
		return fmt.Errorf("invalid manifest")
	}
	all, _ := Skills("fullstack")
	allowed := map[string]bool{}
	for _, n := range all {
		allowed[n] = true
	}
	total := 0
	for k, v := range b.Files {
		total += len(v)
		if !safeName(k) || !allowed[strings.Split(k, "/")[0]] || len(v) > maxFile || total > maxTotal {
			return fmt.Errorf("invalid skill file %s", k)
		}
		if b.Manifest.Files[k] != digest(v) {
			return fmt.Errorf("checksum mismatch: %s", k)
		}
	}
	for _, n := range all {
		v, ok := b.Files[n+"/SKILL.md"]
		if !ok || !bytes.HasPrefix(v, []byte("---\n")) {
			return fmt.Errorf("missing skill frontmatter: %s", n)
		}
		end := bytes.Index(v[4:], []byte("\n---"))
		if end < 0 {
			return fmt.Errorf("invalid frontmatter: %s", n)
		}
		front := string(v[4 : 4+end])
		if !regexp.MustCompile(`(?m)^name: `+regexp.QuoteMeta(n)+`\s*$`).MatchString(front) || !regexp.MustCompile(`(?m)^description: .+`).MatchString(front) {
			return fmt.Errorf("invalid name or description: %s", n)
		}
		if len(b.Files[n+"/agents/openai.yaml"]) == 0 {
			return fmt.Errorf("missing metadata: %s", n)
		}
	}
	// Runtime file links must resolve in each selected scenario, not just the full bundle.
	for _, scenario := range ScenarioNames {
		names, _ := Skills(scenario)
		selected := map[string]bool{}
		for _, n := range names {
			selected[n] = true
		}
		for k, v := range b.Files {
			if !selected[strings.Split(k, "/")[0]] || !strings.HasSuffix(k, ".md") {
				continue
			}
			for _, target := range localLinks(string(v)) {
				resolved := path.Clean(path.Join(path.Dir(k), target))
				if strings.HasPrefix(target, "/") || !safeName(resolved) || b.Files[resolved] == nil || !selected[strings.Split(resolved, "/")[0]] {
					return fmt.Errorf("%s: broken link in %s: %s", scenario, k, target)
				}
			}
		}
	}
	return nil
}

var mdLink = regexp.MustCompile(`\[[^\]\n]*\]\(([^\s)]+)\)`)

func localLinks(s string) []string {
	var result []string
	fence := ""
	for _, line := range strings.Split(s, "\n") {
		t := strings.TrimSpace(line)
		if strings.HasPrefix(t, "```") || strings.HasPrefix(t, "~~~") {
			marker := t[:3]
			if fence == "" {
				fence = marker
			} else if fence == marker {
				fence = ""
			}
			continue
		}
		if fence != "" {
			continue
		}
		for _, m := range mdLink.FindAllStringSubmatch(line, -1) {
			u := m[1]
			if strings.Contains(u, ":") || strings.HasPrefix(u, "#") {
				continue
			}
			result = append(result, strings.SplitN(u, "#", 2)[0])
		}
	}
	return result
}
