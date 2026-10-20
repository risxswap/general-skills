package main

import (
	"bufio"
	"flag"
	"fmt"
	"general-skills/tools/internal/kit"
	"io"
	"os"
	"path/filepath"
	"strings"
)

var version = "dev"

func main() {
	if err := run(os.Args[1:], os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "错误:", err)
		os.Exit(1)
	}
}
func run(args []string, in io.Reader, out io.Writer) error {
	if len(args) > 0 && (args[0] == "--help" || args[0] == "help" || args[0] == "-h") {
		fmt.Fprintln(out, "general-skills [install|package|version]\ninstall: --scenario general|java|frontend|fullstack|testing --scope project|user [--project-dir PATH] [--bundle ZIP] [--conflict fail|skip|replace] [--dry-run]\n无参数进入交互安装。\npackage: --root PATH --output PATH --version X.Y.Z --targets darwin/arm64,windows/amd64,...")
		return nil
	}
	if len(args) > 0 && args[0] == "version" {
		fmt.Fprintln(out, version)
		return nil
	}
	if len(args) > 0 && args[0] == "package" {
		f := flag.NewFlagSet("package", flag.ContinueOnError)
		f.SetOutput(out)
		root := f.String("root", ".", "仓库目录")
		output := f.String("output", "dist", "新建输出目录")
		v := f.String("version", "", "版本号")
		targets := f.String("targets", "darwin/arm64", "目标平台")
		if e := f.Parse(args[1:]); e != nil {
			return e
		}
		if f.NArg() != 0 {
			return fmt.Errorf("unexpected positional arguments")
		}
		if e := kit.Release(*root, *output, *v, *targets); e != nil {
			return e
		}
		fmt.Fprintln(out, "发布包已生成:", *output)
		return nil
	}
	interactive := len(args) == 0 || (len(args) == 1 && args[0] == "install")
	if len(args) > 0 && args[0] != "install" {
		return fmt.Errorf("unknown command %q", args[0])
	}
	f := flag.NewFlagSet("install", flag.ContinueOnError)
	f.SetOutput(out)
	var o kit.Options
	f.StringVar(&o.Scenario, "scenario", "", "使用场景")
	f.StringVar(&o.Scope, "scope", "", "project 或 user")
	f.StringVar(&o.ProjectDir, "project-dir", "", "已有项目目录")
	f.StringVar(&o.Conflict, "conflict", "fail", "同名处理")
	f.BoolVar(&o.DryRun, "dry-run", false, "仅预览")
	exe, e := os.Executable()
	if e != nil {
		return e
	}
	bundlePath := f.String("bundle", filepath.Join(filepath.Dir(exe), "skills.bundle.zip"), "技能包路径")
	if len(args) > 0 {
		if e = f.Parse(args[1:]); e != nil {
			return e
		}
	}
	if f.NArg() != 0 {
		return fmt.Errorf("unexpected positional arguments")
	}
	reader := bufio.NewReader(in)
	ask := func(prompt string) (string, error) {
		fmt.Fprint(out, prompt)
		s, e := reader.ReadString('\n')
		if e != nil {
			return "", fmt.Errorf("输入已结束，未安装: %w", e)
		}
		return strings.TrimSpace(s), nil
	}
	if interactive {
		labels := map[string]string{"general": "通用开发", "java": "Java 后端开发", "frontend": "前端开发", "fullstack": "全栈开发", "testing": "专项测试"}
		choices := make(map[string]string)
		fmt.Fprintln(out, "请选择安装场景：")
		for i, scenario := range kit.ScenarioNames {
			names, err := kit.Skills(scenario)
			if err != nil {
				return err
			}
			choices[fmt.Sprint(i+1)] = scenario
			fmt.Fprintf(out, "%d. %s (%s)\n   技能：%s\n", i+1, labels[scenario], scenario, strings.Join(names, ", "))
		}
		s, e := ask("请输入场景编号: ")
		if e != nil {
			return e
		}
		o.Scenario = choices[s]
		if o.Scenario == "" {
			return fmt.Errorf("无效场景")
		}
		s, e = ask("范围 1=项目级 2=当前用户全局: ")
		if e != nil {
			return e
		}
		switch s {
		case "1":
			o.Scope = "project"
			o.ProjectDir, e = ask("项目目录（必须已存在，无默认值）: ")
			if e != nil {
				return e
			}
		case "2":
			o.Scope = "user"
		default:
			return fmt.Errorf("无效范围")
		}
	}
	dest, e := kit.Destination(o)
	if e != nil {
		return e
	}
	info, e := os.Stat(*bundlePath)
	if e != nil {
		return e
	}
	if info.Size() > 64<<20 {
		return fmt.Errorf("archive too large")
	}
	data, e := os.ReadFile(*bundlePath)
	if e != nil {
		return e
	}
	b, e := kit.Read(data)
	if e != nil {
		return e
	}
	if interactive {
		preview := o
		preview.Conflict = "skip"
		actions, e := kit.Plan(b, preview, dest)
		if e != nil {
			return e
		}
		conflict := false
		fmt.Fprintf(out, "版本 %s，安装位置 %s\n", b.Manifest.Version, dest)
		for _, a := range actions {
			fmt.Fprintf(out, "%s: %s\n", a.Skill, a.Kind)
			if a.Kind == "skip" {
				conflict = true
			}
		}
		if conflict {
			s, e := ask("存在同名技能：1=取消（默认） 2=跳过 3=替换: ")
			if e != nil {
				return e
			}
			switch s {
			case "2":
				o.Conflict = "skip"
			case "3":
				o.Conflict = "replace"
			default:
				fmt.Fprintln(out, "已取消，未安装")
				return nil
			}
		}
		s, e := ask("确认安装？输入 y 继续，其他输入取消: ")
		if e != nil {
			return e
		}
		if strings.ToLower(s) != "y" {
			fmt.Fprintln(out, "已取消，未安装")
			return nil
		}
	}
	actions, e := kit.Install(b, o, dest)
	if e != nil {
		return e
	}
	label := "已安装"
	if o.DryRun {
		label = "预览（未写入）"
	}
	fmt.Fprintf(out, "%s: %s (%s)\n", label, dest, b.Manifest.Version)
	for _, a := range actions {
		fmt.Fprintf(out, "%s: %s\n", a.Skill, a.Kind)
	}
	return nil
}
