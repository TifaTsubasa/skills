---
name: best-ios
description: 按照统一架构规范（Page/Controller/Manager/Store/Service/View/Model）与三层模型设计（Entity/Item/Node），对 iOS 项目进行重构、代码审查或 TDD 式 Bug 修复
---

你需要根据用户的要求，参照约束内的内容，对指定的 iOS 项目或模块执行**重构**、**代码审查**（Review）或**Bug 修复**（Fix）。

## 核心约束

- `references/core/swift-templates.md` 不是可选参考示例，而是**必须遵守的落地模板规范**
- 只要产出或修改 Page / Controller / Manager / Store / Service / View / Model 相关代码，最终结构、职责划分、命名方式与数据流写法都必须与 `swift-templates.md` 保持一致
- 若现有代码与模板冲突，默认以 `swift-templates.md` 为准推进重构、修复或审查；只有用户明确要求保留历史特殊写法时，才允许偏离模板，并且需要在结论中明确指出偏离点与风险

## 参考资料

开始前通读 `references/core/architecture.md` 与 `references/core/swift-templates.md`，确认架构层级、模型分层、数据流、测试范围与标准代码结构；执行过程中按需加载以下文件：

- `references/core/architecture.md` — 架构层级规范、三层模型设计、Event/Command 数据流、单元测试范围（**开始前必读**）
- `references/core/swift-templates.md` — 各层完整 Swift 代码模板（Page / Controller / Manager / Store / Service / View / Model 三层），包含 Event / Command 调度示例（**开始前必读**）
- `references/core/notes.md` — 注意事项速查：编码规范、并发、Event/Command 约束、常见违规、Review 扫描清单
- `references/workflows/refactor-workflow.md` — **Refactor 模式**执行步骤
- `references/workflows/review-workflow.md` — **Review 模式**执行步骤
- `references/workflows/fix-workflow.md` — **Fix 模式**执行步骤（Store 层 TDD 修复流程）

## 判断模式并加载对应流程

先根据用户的原始诉求判断执行模式，然后读取对应的流程文件并严格按其步骤执行：

- **Refactor 模式** — 用户明确要求「重构 / 调整 / 拆分 / 迁移」代码，需要产出改动
  → 读取 `references/workflows/refactor-workflow.md`，按其步骤执行

- **Review 模式** — 用户要求「审查 / 检查 / review / 评估 / 找问题」，只产出问题清单与建议
  → 读取 `references/workflows/review-workflow.md`，按其步骤执行

- **Fix 模式** — 用户描述 bug 且希望用「先以 Store 单测复现、再修复」的 TDD 流程修问题
  → 读取 `references/workflows/fix-workflow.md`，按其步骤执行

若用户表述模糊，先与其确认模式后再加载对应流程文件。
