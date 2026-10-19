# mattpocock 技能参考讨论

日期：2026-10-19。状态：用户已确认增加 diagnosing-bugs 与 code-review，两项已作为本套适配技能实现；其余仍为建议，未安装上游插件。

## 观察

[mattpocock/skills](https://github.com/mattpocock/skills) 将工程方法组织为可组合的小技能。已读取当前 README，以及 diagnosing-bugs、tdd、code-review、codebase-design、domain-modeling 和 grilling 的入口。本文只比较这些内容，不声称审阅完整仓库及所有配套参考。

本套现有 Java/Vue 技能负责技术规则；缺口主要在“怎样诊断、怎样验证、怎样审查”的执行方法。建议保留两类职责，工作流按需要加载，不把所有方法合成一个默认执行的长流程。

## 优先讨论的能力

| 上游参考 | 对本套的价值 | 建议处置 |
| --- | --- | --- |
| [diagnosing-bugs](https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnosing-bugs/SKILL.md) | 建立能捕获原问题的反馈，再检验假设、最小化复现并回归 | 优先独立技能，面向复杂缺陷；简单错误保留轻量路径 |
| [code-review](https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md) | 分别审查是否符合规范、是否实现需求 | 优先独立技能，复用阿里映射与项目规格；报告区分两类问题 |
| [tdd](https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md) | 从公共行为验证，一次实现一个可验证切片 | 作为按需方法，用户选择测试先行或高风险业务时启用 |
| [domain-modeling](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/SKILL.md) | 消除业务术语歧义，记录确有取舍的重要决定 | 有术语冲突时使用；词汇表与架构决定按实际内容建立 |
| [codebase-design](https://github.com/mattpocock/skills/blob/main/skills/engineering/codebase-design/SKILL.md) | 减少调用方需要知道的细节，提高模块可测试性 | 先作为设计参考；不强制单体 DDD 化或增加接口层 |
| [grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md) | 按决策依赖澄清，而不是随机提问 | 用户要求深入讨论时采用，不在每次修改前强制盘问 |

## 需要适配的地方

上游 TDD 要求写测试前确认测试边界。本套建议沿用已批准规格和既有测试边界，只有边界实质改变时澄清。测试应验证业务行为；数据库事务集成测试仍可通过独立读取检查真实持久化结果，不能把这种必要证据一概当成实现耦合。

上游诊断技能在无法建立反馈时停止进入假设阶段。本套建议保留证据要求，同时允许把静态分析发现明确标注为候选原因，不能将其当已验证根因或已修复结果。

上游代码审查使用并行子 Agent。本套可以采用规范与需求两个审查维度，执行方式根据任务授权和环境决定，不让子 Agent 成为所有审查的必需依赖。还应区分已提交分支和未提交工作区的实际审查范围。

上游深模块设计和领域建模带有自己的术语及文件约定。Java 的 interface 关键字不等于设计层面的对外契约；采用方法时仍保留项目已有业务术语与文档目录，避免为了统一术语重新命名全仓。

humanizer-zh 只调整表达，不削弱这些工程规则的完成条件、强制等级和不确定性。

## 建议路线

下一轮优先落地 diagnosing-bugs 和 code-review，保持独立入口，公共工作流只增加条件路由。TDD 作为可选能力随后加入；术语建模和设计方法等遇到真实需求再补充。

也可以选择只吸收方法到现有 references，以减少技能数量。代价是诊断与审查不容易单独调用，后续规则增长时仍可能需要拆分。

待讨论的是能力组合和触发方式，并非技术版本选择。两项已实现技能固定来源提交并保留 MIT 许可证；其余上游材料仍仅用于研究。

## 已确认结果

两个独立入口已接入公共开发流程的条件路由，沿用只诊断/只审查边界，不强制并行 Agent。原“建议路线”保留为决策背景；TDD 尚未纳入实施；业务建模随后按用户决定以 business-modeling 实施，限定 MVC 业务概念梳理。

## 业务建模决定

采用独立 business-modeling，而非原样引入 domain-modeling。沿用业务概念澄清方法，保留简单 MVC 架构，维护现有文档且按需创建资料；不自动生成 DDD 层次或强制 ADR。
