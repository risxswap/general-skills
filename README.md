# General Skills

一套可组合的开发技能，覆盖需求讨论、业务建模、开发实现、缺陷诊断、代码审查和中文文档整理。目前提供 Java 后端与通用前端专项，通过 Go 安装工具按使用场景安装到项目或当前用户目录。

项目的产品形态、运行平台、架构和技术栈由 `AGENTS.md` 定义。已有项目缺少说明时，先分析代码与配置，再与用户沟通确认；新项目引导用户选择，确认后按授权记录。技能不预设 MVC、Spring Boot、Vue 或 TypeScript。

## 技能

| 技能 | 用途 |
| --- | --- |
| [development-workflow](skills/development-workflow/SKILL.md) | 区分讨论、规格整理、实施、诊断和审查，按用户行为组织开发与验证 |
| [business-modeling](skills/business-modeling/SKILL.md) | 澄清业务术语、对象关系、状态和约束，沿用项目架构 |
| [java-backend](skills/java-backend/SKILL.md) | Java 规约、接口、数据访问、事务、并发与后端验证 |
| [frontend-development](skills/frontend-development/SKILL.md) | 页面、组件、状态、接口、交互和目标平台验证 |
| [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md) | 建立失败证据、检验候选原因并验证修复 |
| [code-review](skills/code-review/SKILL.md) | 分别审查规范符合性与需求实现，报告有依据的发现 |
| [humanizer-zh](skills/humanizer-zh/SKILL.md) | 润色中文文档，保留事实、技术约束和完成状态 |

前端技能分别考虑使用场景（管理后台、面向消费者）、运行平台（Web、小程序、桌面或移动客户端）和技术实现，按任务组合使用。已有 Vue 专属参考仅在项目使用 Vue 时加载；其他技术沿用项目规范和对应官方资料。

Java 技能采用阿里巴巴 Java 开发手册的已映射子集，规则等级与适配依据见 [来源映射](skills/java-backend/references/alibaba-rule-mapping.md)。Spring Boot 单体实践为条件参考，不代表默认架构；当前不包含微服务专项规范。

## 安装

使用与当前源码对应的平台包，解压后运行 `general-skills`，Windows 运行 `general-skills.exe`。无参数进入交互安装，由用户选择场景与安装范围，不自动探测项目。尚无对应发布包时，可按下文从源码打包。

| 场景 | 安装内容 |
| --- | --- |
| `general` | 开发流程、业务建模、缺陷诊断、代码审查、中文润色 |
| `java` | 通用配套 + Java 后端 |
| `frontend` | 通用配套 + 前端开发 |
| `fullstack` | 全部七个技能 |

项目级安装到 `<项目>/.agents/skills`，用户级安装到 `~/.agents/skills`。项目级需指定已有目录；安装场景只决定安装哪些技能，不决定业务项目的架构或技术栈。

```sh
# 预览项目级前端安装，不写入文件
./general-skills install --scenario frontend --scope project --project-dir /path/to/project --dry-run

# 安装 Java 开发配套到项目
./general-skills install --scenario java --scope project --project-dir /path/to/project

# 安装全部技能到当前用户目录
./general-skills install --scenario fullstack --scope user
```

保留可执行文件旁的 `skills.bundle.zip`，或用 `--bundle PATH` 指定技能包。使用已构建的平台包安装无需 Go、Python 或网络。

遇到同名技能，命令行默认停止；`--conflict skip` 保留已有版本，`--conflict replace` 完整替换所选技能目录，包括其中的自定义文件。交互模式会展示安装位置和技能，遇到冲突再选择处理方式。安装新场景不会删除未选技能，也不会改动业务源码。

**旧版迁移：** `vue-frontend` 已更名为 `frontend-development`，场景参数 `vue` 改为 `frontend`。安装器不自动删除旧技能，也不迁移 `.codex/skills` 等其他目录中的副本。检查并保存自定义内容后再移除旧副本，避免重复加载。旧版发布包仍保留旧命名，需要重新构建才能包含此次改造。

## 使用示例

可直接点名技能，也可通过任务描述触发：

```text
使用 $development-workflow，把刚才讨论的内容整理到现有需求规格，先不实施。
使用 $business-modeling，梳理订单取消与退款的业务含义，先只讨论。
使用 $java-backend，修复订单多步写入未回滚的问题并验证。
使用 $frontend-development，修复筛选请求乱序覆盖列表的问题。
使用 $diagnosing-bugs，定位偶发重复扣减，先只诊断。
使用 $code-review，审查当前所有未提交修改，包含新增文件。
使用 $humanizer-zh，润色这份中文说明，保留技术约束和验证状态。
```

开发流程按任务调用建模、诊断、审查和技术参考；它们也能独立使用。局部修改采用轻量流程，讨论或整理规格不会自动进入实施，只审查不会自动修复。Java 后端与前端专项按安装场景提供，未安装时沿用项目规范并说明缺口。

各技能复用项目已有资料：`AGENTS.md` 记录项目约定，词汇表解释业务概念，Issue / Spec 描述需求与验收条件，ADR 记录重要取舍。详细规则见 [项目约定](skills/development-workflow/references/project-conventions.md)。

## 从源码打包

需要 Go 1.25+、Python 3 和 PyYAML。Go 打包与安装代码位于 `tools/`，仅使用标准库；`package.sh` 先运行技能结构检查，再构建平台包。

在仓库根目录执行：

```sh
./package.sh

# 只构建指定平台，输出目录必须不存在
TARGETS=darwin/arm64,windows/amd64 OUTPUT=/tmp/general-skills-release ./package.sh

# 直接调用 Go 打包器，执行内置包结构与场景引用检查
# 此命令不代替 Python 技能元数据检查
go -C tools run ./cmd/general-skills package --root .. --version 0.1.0 --output ../dist/custom --targets darwin/arm64
```

版本读取 `VERSION`，也可通过同名环境变量覆盖。默认构建 macOS、Windows、Linux 的 amd64/arm64 六个平台包，输出到 `dist/<版本>/`，已存在的目录不会覆盖。每个 ZIP 包含原生 CLI、技能包、使用说明和校验清单，外部另附 SHA-256。安装冲突、恢复方式和验证边界见 [打包安装说明](docs/packaging.md)。

## 维护与验证

```sh
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
go -C tools test ./...
go -C tools test -race ./...
go -C tools vet ./...
```

Python 检查覆盖技能元数据、本地文件链接、参考可达性和配套布局；Go 测试覆盖安装场景、包校验、冲突处理及失败回滚。结构检查通过不代表 Agent 行为正确。[行为评估场景](tests/skill-evals/README.md)与实际执行证据分开维护，尚未运行的场景不计为通过。

## 参考与来源

- 阿里巴巴 Java 开发手册：版本、来源与采纳范围见 [规则映射](skills/java-backend/references/alibaba-rule-mapping.md)。
- mattpocock 方法适配：见 [诊断来源](skills/diagnosing-bugs/references/provenance.md)、[审查来源](skills/code-review/references/provenance.md)及[建模来源](skills/business-modeling/references/provenance.md)，相应目录保留上游许可证。
- humanizer-zh 使用技术文档适配版，保留 [MIT 许可证](skills/humanizer-zh/references/LICENSE)。

历史方案与演进记录见 [设计文档](docs/java-vue-skills-design.md)、[实施记录](docs/implementation.md)和[参考讨论](docs/mattpocock-discussion.md)；当前用法以本 README 和技能入口为准。
