# General Skills

一套可组合的开发技能，覆盖需求讨论、业务建模、开发实现、缺陷诊断、代码审查、接口与 UI 黑盒测试和中文文档整理。目前提供 Java 后端与通用前端专项，通过 Go 安装工具按使用场景安装到项目或当前用户目录。

项目的产品形态、运行平台、架构和技术栈由 `AGENTS.md` 定义。已有项目缺少说明时，先分析代码与配置，再与用户沟通确认；新项目引导用户选择，确认后按授权记录。技能不预设 MVC、Spring Boot、Vue 或 TypeScript。

## 技能

| 技能 | 用途 |
| --- | --- |
| [development-workflow](skills/development-workflow/SKILL.md) | 统一组织需求、领域建模、技术设计、实施与验证，按需调用诊断和审查 |
| [java-backend](skills/java-backend/SKILL.md) | Java 规约、接口、数据访问、事务、并发与后端验证 |
| [frontend-development](skills/frontend-development/SKILL.md) | 页面结构、视觉方向、设计规范、组件实现、接口交互和目标平台验证 |
| [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md) | 建立失败证据、检验候选原因并验证修复 |
| [code-review](skills/code-review/SKILL.md) | 优先审查真实缺陷与需求遗漏，独立复核并记录复审状态 |
| [testing-workflow](skills/testing-workflow/SKILL.md) | 组织接口与 UI 黑盒测试的覆盖、用例、计划、报告和缺陷复验 |
| [api-testing](skills/api-testing/SKILL.md) | 按接口契约通过 curl 执行黑盒测试并保存脱敏证据 |
| [ui-testing](skills/ui-testing/SKILL.md) | 通过真实浏览器或已有 Playwright 验证页面与业务链路 |
| [humanizer-zh](skills/humanizer-zh/SKILL.md) | 润色中文文档，保留事实、技术约束和完成状态 |

前端技能分别考虑使用场景（管理后台、面向消费者）、运行平台（Web、小程序、桌面或移动客户端）和技术实现，按任务组合使用。已有 Vue 专属参考仅在项目使用 Vue 时加载；其他技术沿用项目规范和对应官方资料。

界面设计合并在 `frontend-development` 中：新产品和整体改版按需确定视觉方向与全局规范，新增页面继承既有设计，局部修改保持轻量。设计方法、规范维护和实际呈现检查按需加载；讨论与实施沿用当前授权，设计文档区分提案、已确认、已实现和已验证状态。

Java 技能采用阿里巴巴 Java 开发手册的已映射子集，规则等级与适配依据见 [来源映射](skills/java-backend/references/alibaba-rule-mapping.md)。Spring Boot 单体实践为条件参考，不代表默认架构；当前不包含微服务专项规范。

## 安装

使用与当前源码对应的平台包，解压后运行 `general-skills`，Windows 运行 `general-skills.exe`。无参数进入交互安装，由用户选择场景与安装范围，不自动探测项目。尚无对应发布包时，可按下文从源码打包。

| 场景 | 用途 | 安装内容 |
| --- | --- | --- |
| `general` | 通用开发 | 开发流程（含领域建模与技术设计）、缺陷诊断、代码审查、中文润色，共 4 个技能 |
| `java` | Java 后端开发 | 通用开发 + Java 后端 + 测试技能组，共 8 个技能 |
| `frontend` | 前端开发 | 通用开发 + 前端开发 + 测试技能组，共 8 个技能 |
| `fullstack` | 全栈开发 | 全部 9 个技能 |
| `testing` | 专项测试 | 仅测试技能组，共 3 个技能 |

测试技能组包含 `testing-workflow`（测试组织与报告）、`api-testing`（接口黑盒测试）和 `ui-testing`（页面交互与业务链路测试），三个技能一起安装。

`general` 场景不再包含测试技能组；已有安装中的测试技能不会自动删除。需要补充测试能力时，可在同一安装范围安装 `testing` 场景。

项目级安装到 `<项目>/.agents/skills`，用户级安装到 `~/.agents/skills`。项目级需指定已有目录；安装场景只决定安装哪些技能，不决定业务项目的架构或技术栈。

```sh
# 预览项目级前端安装，不写入文件
./general-skills install --scenario frontend --scope project --project-dir /path/to/project --dry-run

# 安装 Java 开发配套到项目
./general-skills install --scenario java --scope project --project-dir /path/to/project

# 仅安装测试技能组到项目
./general-skills install --scenario testing --scope project --project-dir /path/to/project

# 安装全部技能到当前用户目录
./general-skills install --scenario fullstack --scope user
```

保留可执行文件旁的 `skills.bundle.zip`，或用 `--bundle PATH` 指定技能包。使用已构建的平台包安装无需 Go、Python 或网络。

遇到同名技能，命令行默认停止；`--conflict skip` 保留已有版本，`--conflict replace` 完整替换所选技能目录，包括其中的自定义文件。交互模式会展示安装位置和技能，遇到冲突再选择处理方式。安装新场景不会删除未选技能，也不会改动业务源码。

**旧版迁移：** `business-modeling` 已合并进 `development-workflow`，新包不再包含独立建模技能。 `vue-frontend` 已更名为 `frontend-development`，场景参数 `vue` 改为 `frontend`。安装器不自动删除旧技能，也不迁移 `.codex/skills` 等其他目录中的副本。检查并保存自定义内容后再移除旧副本，避免重复加载。旧版发布包仍保留旧命名，需要重新构建才能包含此次改造。

## 使用示例

可直接点名技能，也可通过任务描述触发：

```text
使用 $development-workflow，把刚才讨论的内容整理到现有需求规格，先不实施。
使用 $development-workflow，梳理订单取消与退款的业务含义，先只讨论。
使用 $java-backend，修复订单多步写入未回滚的问题并验证。
使用 $frontend-development，修复筛选请求乱序覆盖列表的问题。
使用 $diagnosing-bugs，定位偶发重复扣减，先只诊断。
使用 $code-review，审查当前所有未提交修改，包含新增文件。
使用 $api-testing，按接口文档验证订单取消接口并保存证据。
使用 $ui-testing，按验收标准验证订单页面和取消流程。
使用 $testing-workflow，组织订单模块的接口与 UI 正式回归并生成报告。
使用 $humanizer-zh，润色这份中文说明，保留技术约束和验证状态。
```

开发流程内部按任务加载需求、领域建模与技术设计参考，诊断、审查和技术专项仍可独立使用。局部修改采用轻量流程，讨论或整理规格不会自动进入实施，只审查不会自动修复。Java 后端与前端专项按安装场景提供，未安装时沿用项目规范并说明缺口。

架构和数据库讨论形成阶段性结论时，会将其中新增或调整的预期行为同步到需求 Spec，并引用详细设计。未确认内容保留为草案，已确认且尚未开发的内容标为待实现；记录需求无需等待编码授权。

开发中调整架构抽象、模块职责或依赖关系时，同步项目总览中受影响的设计说明和图示；涉及领域、数据库或功能变化时同步对应文档，交付前核对代码、总览和需求记录的一致性。

默认项目文档使用编号中文目录：`docs/01-项目总览/` 保存功能总览、领域模型、架构和数据库设计；`02-需求文档/` 与 `03-BUG修复/` 按日期和中文主题记录工作；`04-技术决策/` 保存重要取舍；`05-代码审查/` 直接保存按日期、中文主题和轮次命名的审查报告，不增加周期子目录。简单需求或 BUG 默认一份说明，复杂时再拆方案和验证；已有项目沿用原约定。

各技能复用项目已有资料：`AGENTS.md` 记录项目约定，词汇表解释业务概念，Issue / Spec 描述需求与验收条件，ADR 记录重要取舍。详细规则见 [项目约定](skills/development-workflow/references/project-conventions.md)。

测试技能及公共工作流迁移自 `guma-develop-skill/skills`，三个技能共同安装，保留原有模板、覆盖规则和报告脚本。正式测试资产沿用 `docs/testing/` 与 `docs/plan/`；测试脚本使用 Python 3.10+ 标准库，通过 `python3` 调用，实际接口执行需要 curl，UI 执行需要可用浏览器工具或项目已有 Playwright。

## 从源码打包

需要 Go 1.25+、Python 3 和 PyYAML。Go 打包与安装代码位于 `tools/`，仅使用标准库；`package.sh` 先运行技能结构检查，再构建平台包。

在仓库根目录执行：

```sh
./package.sh

# 只构建指定平台；自定义输出目录必须不存在
TARGETS=darwin/arm64,windows/amd64 OUTPUT=/tmp/general-skills-release ./package.sh

# 直接调用 Go 打包器，执行内置包结构与场景引用检查
# 此命令不代替 Python 技能元数据检查
go -C tools run ./cmd/general-skills package --root .. --version 0.1.0 --output ../dist/custom --targets darwin/arm64
```

版本读取 `VERSION`，也可通过同名环境变量覆盖。默认只构建 macOS ARM64，直接输出到 `dist/`，不使用版本子目录或带版本号的包名；版本仍写入 CLI 和技能清单。`package.sh` 重复执行时会先清空默认 `dist/`；指定 `OUTPUT` 时保留目标目录的安全校验，目标必须不存在。可用 `TARGETS` 指定其他平台。同时保留 `dist/general-skills-darwin-arm64/` 安装目录，可直接运行其中的安装器。每个 ZIP 包含原生 CLI、技能包、使用说明和校验清单，外部另附 SHA-256。安装冲突、恢复方式和验证边界见 [打包安装说明](docs/packaging.md)。

## 维护与验证

```sh
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/testing-workflow -p 'test_*.py'
go -C tools test ./...
go -C tools test -race ./...
go -C tools vet ./...
```

Python 检查覆盖技能元数据、本地文件链接、参考可达性和配套布局；Go 测试覆盖安装场景、包校验、冲突处理及失败回滚。结构检查通过不代表 Agent 行为正确。[行为评估场景](tests/skill-evals/README.md)与实际执行证据分开维护，尚未运行的场景不计为通过。

## 规范与许可

- 阿里巴巴 Java 开发手册：版本、来源与采纳范围见 [规则映射](skills/java-backend/references/alibaba-rule-mapping.md)。
- humanizer-zh 使用技术文档适配版，保留 [MIT 许可证](skills/humanizer-zh/references/LICENSE)。

本套技能按项目需求独立设计和维护，职责、触发条件及交付要求以仓库内规则为准。

历史方案与演进记录见 [设计文档](docs/java-vue-skills-design.md)、[实施记录](docs/implementation.md)；当前用法以本 README 和技能入口为准。
