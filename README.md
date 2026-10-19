# Java + Vue 开发技能

提供开发流程、Java 后端与前端专项和配套方法技能。架构与技术栈由项目 `AGENTS.md` 定义；缺少定义时，已有项目先分析实现，再与用户沟通确认，新项目引导用户选择，确认后记录。安装场景只选择技能，不决定项目架构。

| 技能 | 用途 |
| --- | --- |
| [development-workflow](skills/development-workflow/SKILL.md) | 任务分流、行为切片、跨层契约与证据验收 |
| [java-backend](skills/java-backend/SKILL.md) | 阿里规范映射、Java 实践、事务与服务端安全 |
| [frontend-development](skills/frontend-development/SKILL.md) | 页面与组件、接口、交互和目标平台验证 |
| [humanizer-zh](skills/humanizer-zh/SKILL.md) | 中文文档润色，保护事实、技术约束与完成状态 |
| [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md) | 复杂缺陷与性能回退的证据驱动诊断 |
| [code-review](skills/code-review/SKILL.md) | 分别审查代码规范与需求实现 |
| [business-modeling](skills/business-modeling/SKILL.md) | 澄清术语、关系、状态与约束，沿用项目架构 |

## 使用

下载对应平台发布包，解压后运行 `general-skills`（Windows 为 `general-skills.exe`），按提示选择场景、项目级或用户级安装。不探测项目技术栈，项目级必须输入已有目录。

| 场景 | 技能 |
| --- | --- |
| `general` | 开发流程、业务建模、诊断、审查、中文润色 |
| `java` | 通用配套 + Java 后端 |
| `frontend` | 通用配套 + 前端开发 |
| `fullstack` | 全部七个技能 |

项目级写入 `<项目>/.agents/skills`，用户级写入 `~/.agents/skills`，依据 [Codex 官方本地技能目录](https://learn.chatgpt.com/docs/build-skills)。不会修改旧 `.codex/skills`、用户的插件或业务源码；已有其他位置的同名技能需自行选择，避免重复触发。

```sh
./general-skills install --scenario java --scope project --project-dir /path/to/project
./general-skills install --scenario fullstack --scope user
./general-skills install --scenario frontend --scope project --project-dir /path/to/project --dry-run
```

CLI 默认从可执行文件旁读取 `skills.bundle.zip`，与启动目录无关；也可通过 `--bundle PATH` 指定。发布包安装无需 Go、Python或网络。命令行遇到同名技能默认失败，显式使用 `--conflict skip` 保留原技能，或 `--conflict replace` 替换所选技能目录；替换会移除目录内旧文件及自定义文件。交互模式会先显示目录和技能，遇到冲突再选择取消、跳过或替换。

Java 后端与前端开发是可选专项，公共技能会先检查是否安装再读取；必需公共配套随每个场景安装。安装新场景不删除旧场景之外的技能。跳过已有技能保留其原版本，安装器不能保证用户自定义版本的语义兼容。

可以直接点名 `$java-backend`、`$frontend-development` 或 `$development-workflow`；也支持根据描述自动识别。示例：“使用 $java-backend 修复订单多步写入未回滚的问题”；“使用 $frontend-development 修复筛选请求乱序覆盖列表的问题”。

手册已核对的子集、固定版本与适配说明见 [来源映射](skills/java-backend/references/alibaba-rule-mapping.md)。不包含微服务规范，不声称覆盖整个阿里手册。Java、Spring Boot 与 UI 库具体版本在业务项目中确定。

## 维护与验证

用 Python 3 和 PyYAML 执行本仓库检查：

```sh
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

此外，对每个技能使用环境提供的 skill-creator `scripts/quick_validate.py <skill-directory>` 校验。仓库检查验证技能 frontmatter、界面元数据、相对文件链接、从各技能自身入口到其嵌套参考的可达性，以及配套布局；不检查外网可用性或 Markdown 锚点，也不证明 Agent 行为正确。

[行为场景](tests/skill-evals/README.md)用于后续隔离评测；场景定义与执行证据分离，尚未实跑的场景不能算通过。

设计与实施状态分别见 [方案](docs/java-vue-skills-design.md)和[实施记录](docs/implementation.md)。

中文文档生成和修改通过开发流程调用 humanizer-zh，也可单独点名使用。该技能复用参考项目的技术文档适配版，保留 [MIT 许可证](skills/humanizer-zh/references/LICENSE)。后续工程技能取舍见 [mattpocock 参考讨论](docs/mattpocock-discussion.md)。

方法技能可以直接调用，例如：“使用 $diagnosing-bugs 定位偶发重复扣减，先只诊断”；“使用 $code-review 审查所有未提交修改，包含新增文件”。两项均按上游 MIT 许可改写，来源与适配分别记录在各自 references/provenance.md。

开发流程先识别讨论、实施、诊断或审查模式；跨层功能按用户行为切片推进，分别记录实现和验证状态。局部修改保留轻量路径，不新增逐片审批或强制 TDD。

业务建模可直接调用：“使用 $business-modeling 梳理订单取消与退款的含义，先只讨论”。实现沿用项目 `AGENTS.md` 中确认的架构；已有业务定义明确时直接沿用。

各技能共用项目已有资料：词汇表解释业务概念，Issue / Spec 描述行为，ADR 记录重要取舍。没有资料时按需创建，不增加交接文件。

需要沉淀讨论时，可说“把刚才讨论的内容整理成需求规格”。开发流程会归纳已定行为、决定、验证方式和未决项，优先更新已有 Spec，不自动实施或发布 Issue。

## 打包工具

Go 源码位于 `tools/`，仅使用标准库，需要 Go 1.25+。`package.sh` 是打包入口，打包前使用现有 Python/PyYAML 校验；核心打包和安装逻辑均为 Go。

```sh
./package.sh
# 只构建指定平台，输出到新的目录
TARGETS=darwin/arm64,windows/amd64 OUTPUT=/tmp/general-skills-release ./package.sh
# 直接使用 Go 打包（执行内置包结构与场景引用校验）
go -C tools run ./cmd/general-skills package --root .. --version 0.1.0 --output ../dist/custom --targets darwin/arm64
```

版本默认读取 `VERSION`，可通过同名环境变量覆盖。默认构建 macOS、Windows、Linux 的 amd64/arm64 六个平台包，输出 `dist/<版本>/`；输出目录已存在则拒绝覆盖。每个 ZIP 含原生 CLI、技能 ZIP、使用说明和校验清单，外部另附 SHA-256。完整维护和恢复说明见 [打包安装设计](docs/packaging.md)。

```sh
go -C tools test ./...
go -C tools test -race ./...
go -C tools vet ./...
```

前端技能已从 `vue-frontend` 更名为 `frontend-development`，安装场景改为 `frontend`。已有安装不会自动删除旧目录；迁移时先检查旧技能是否包含自定义内容，再由用户移除旧副本，避免同时加载两份规则。
