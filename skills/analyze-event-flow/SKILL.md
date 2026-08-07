---
name: analyze-event-flow
description: 针对**单个 Event** 在 Store 内的影响做聚焦审计：摘出该 Event 触发的状态变更、派发的 Commands，以及每个 Command 在 Controller 路由层最先调用的能力（Manager 方法 / 服务 / 导航），并把结果写入 `docs/event-flow/<Store>/<event>.md`。当用户指定 Store.Event，或用「下拉刷新」「点击删除按钮」这类具体场景询问「这个事件做了什么 / 改了哪些状态 / 派发了哪些 Command / 调用了什么服务 / 影响了什么」时触发本 skill。
---

你需要根据用户指定的 `<Store>` + `<Event>`，到代码里把这一个 Event 在 Store 内的影响摘清楚——只看一个 Event，不画时序图，不追闭环回流。交付物是一份 Markdown 文件，固定包含「状态变更」和「Commands」两节，写入 `docs/event-flow/<Store>/<event>.md`。

本 skill 的概念底座（Store / Command / Manager / Service 的职责与 Event/Command 数据流）以 `../best-ios/references/core/architecture.md` 为准。

## 1. 锁定输入

开始前必须明确两件事：

1. **Store**：哪个 `XxxStore.swift`（一般在 `Packages/PhotosCore/Sources/PhotosCore/Store/` 或其他 Store 目录）。
2. **Event**：Store 的 `Event` 枚举里的具体 case。

如果用户只给了其中一项（例如只说了 Event 名）或描述含糊（例如「点删除按钮的事件」），先用一句话复述你理解的 `<Store>.<Event>` 跟用户确认，**不要硬猜直接写**。猜错就整篇跑偏。

如果用户是按场景描述（「下拉刷新」「点 X 按钮」）而不是 Event case，先执行当前 skill 内的「场景反查」流程，把场景收敛到唯一 `<Store>.<Event>` 后再继续；如果无法唯一定位，先说明候选项并请用户确认，不要硬猜。

如果用户要看多个 Event、完整闭环、Mermaid 时序图或 Manager/Service 内部调用链，也先收敛为单个 Event：可以建议拆成多份单 Event 影响分析；当前 skill 不画图、不追完整闭环。

### 1.1 场景反查

用户没有直接给 Event case 时，用下面的轻量流程从场景定位到 Store Event：

1. 在 View / Page / Controller 中搜索场景关键词、按钮标题、方法名、`send(.`、`store.send`、`handle`、`onTapGesture`、`Button`、`refreshable` 等入口。
2. 沿调用链只追到第一次向 Store 发送 Event 的位置，记录候选 `<Store>.<Event>`。
3. 如果只有一个候选，按这个 Event 继续做影响分析，并在输出文件开头写一行场景背景。
4. 如果有多个候选，按「页面 / 控件 / 条件」列出候选并向用户确认。
5. 如果找不到候选，说明已搜索的入口和缺口，不要编造 Event。

## 2. 工作流程

### 2.1 定位 Event handler

打开 Store.swift，在 `send(_ event:)`（或等价的事件入口方法）里找到 `case .<event>:` 分支。把这个分支整段读出来，包括：

- 直接的赋值语句（`state.x = y`）
- 直接的 `dispatch(commands: [...])` 调用
- 调用的私有 helper（例如 `handleMonthNavigationLoaded(task)`）

**helper 必须递归展开**：helper 内部的 `state.x = y` 和 `dispatch(...)` 都要算到这个 Event 头上，因为它们是这次 Event 处理的一部分。helper 里再嵌套调用别的 helper 也继续展开，直到不再产生状态变更或 dispatch 为止。

> 这件事重要的原因：很多 Store 习惯把复杂分支抽成 `handleXxx()` 私有方法，case 本身只剩一行。如果不展开，会漏掉真实的状态变更和 Command。

### 2.2 摘状态变更

在展开后的整段处理里，把所有**对 `state` 字段或共享状态的赋值**都列出来：

- `state.viewStatus = .loading` → 写成 `state.viewStatus → .loading`
- `state.mode = mode` → 写成 `state.mode → 用户选中的 mode`（值依赖入参时给出语义）
- 改了集合（append / remove / 重建）也要写，写改动语义（如 `state.monthTasks → 替换为最新任务列表`）

要求：

- 只写**这个 Event 直接造成的状态变更**，不要把别的 Event 才会触发的字段也列上来。
- 不写文件:行号、不写源码片段，写**字段名 + 终态语义**，让人一眼看懂改了什么。
- 没有任何状态变更时，明确写「无」，不要省略这一节。

### 2.3 摘 Commands

按 `dispatch(commands:)` 出现的顺序把派发的 Command 列出来。一次 Event 处理里：

- 一次 dispatch 派发多个 Command（数组里多个元素）→ 每个 Command 单独占一行
- 多次 dispatch（条件分支或顺序逻辑）→ 按出现顺序合并到同一份列表里
- 条件分支只在某些情况下 dispatch → 在那条 Command 后面用「仅 xxx 时派发」标注条件，不要再起一个分支段

如果这个 Event 没有派发任何 Command（直接 `break` 或纯状态更新），在 Commands 节明确写「无」。

### 2.4 追每个 Command 的「一层能力」

对每个 Command，定位它在 **Controller 的 `route(_ command:)`**（或等价的 Command 观察入口，例如 `case .xxx:` switch、`commandSubject.sink`）里的处理分支，把这个分支**最先调用的那一层**记下来。

「一层能力」指的是 Controller route 出来的**直接动作**，比如：

- 调用 Manager 方法：`manager.warmUpRuntimeDependencies()`
- 调用 Controller 内部封装的 helper：`await loadMonthTasks(workflowKind)`（再调 manager / service）
- 触发导航：`presentTimelineArrange(task:cachedDeleteAssetIds:)`
- 弹 Alert / 路由到子页面

**不要再往下追到 Manager 内部、Service 内部、数据库层**——本 skill 只到 route 这一跳。

记录格式：每个 Command 一个一级 bullet，下面用二级 bullet 写「调用了 X，做了 Y」。「做了 Y」用一句白话概括语义（来自方法名或注释，不要照抄签名）。常见情况：

- Command 在 route 里只调一个能力 → 只一条二级 bullet
- Command 在 route 里调了多个能力（少见，但有）→ 多条二级 bullet
- Command 在 route 里**找不到对应分支** → 二级 bullet 写「未在 Controller route 中找到映射」，不要编造能力名

### 2.5 落盘

成果**必须**写到 `docs/event-flow/<Store>/<event>.md`：

- `<Store>` 目录用 Store 类型名创建，保持源码里的实际大小写，例如 `ArrangeMonthStore` / `TimelineArrangeStore`
- `<event>.md` 用 Event case 名创建，保持源码里的实际大小写，例如 `monthCardTapped.md` / `deleteCurrentTapped.md`
- 如果 Event 带关联值，只使用 case 名，不把关联值标签写进文件名
- 如果对应路径已经存在 Markdown 文件，生成新内容后**直接覆盖原文件**，不要换文件名
- 用 Write 工具写入；写完只在对话里贴文件路径 + 不超过 3 行的概述（结论 / 是否有空转 / 关键条件分支），完整内容以文件为准

## 3. 输出模板

文件按以下结构组织，**小节标题原样使用**：

```markdown
# <Store>.<event> 影响分析

<可选一行背景：什么交互/上一跳 Event/外部回调会进入这个 case；冷启动 / 已授权之类的前提也写在这里>

## 状态变更

- `state.<字段>` → <终态语义>
- `state.<字段>` → <终态语义>
（如果什么都没改，写「无」）

## Commands

- <commandName1>
  - 调用了 <能力>，做了 <概括>
- <commandName2>
  - 调用了 <能力>，做了 <概括>
  - 调用了 <能力>，做了 <概括>
（如果完全没派发，写「无」）

## 备注（可选）

- 条件分支说明：xxx 时才派发 yyy
- 违反架构约束的特殊处理
- 未在 route 中找到映射的 Command 列表
```

## 4. 示例（节选）

输入：`ArrangeMonthStore.monthCardTapped`

```markdown
# ArrangeMonthStore.monthCardTapped 影响分析

用户在月份页点击某个月任务卡片时进入这个 case。

## 状态变更

- 无

## Commands

- checkMembershipAccess(taskId:)
  - 调用了 `checkMembershipAccess(taskId:)`，做了会员状态校验，校验结果通过 `.membershipAccessChecked` Event 回流

## 备注

- 这是一个纯派发型 Event，自身不改状态；后续 `.allowed` / `.denied` 的分支处理在 `.membershipAccessChecked` Event 里。
```

输入：`ArrangeMonthStore.pageDidLoad`

```markdown
# ArrangeMonthStore.pageDidLoad 影响分析

页面首次加载（`viewDidLoad` 路径）触发的 Event。

## 状态变更

- `state.viewStatus` → `.loading`

## Commands

- loadMonthTasks(workflowKind: .initialLoad)
  - 调用了 `loadMonthTasks(_:)`，做了月份任务列表的初次拉取，完成后通过 `.monthTasksResolved` Event 回流
```

## 5. 约束

- **必须落盘到 `docs/event-flow/<Store>/<event>.md`**。只在对话里贴答复是不合格的。
- **只追一个 Event**。如果用户给了多个 Event、想要全 Store 审计、想画 Mermaid 或想看完整闭环，先确认并拆成多次任务（每个 Event 一个文件）；不要在一份文档里混写多个 Event。
- **只到 route 这一层**。Command 在 Controller 之外的进一步去向不在范围内；如果用户想看 Manager/Service 内部，先把需求收敛到一个 Command 或另开更具体的分析任务。
- **不虚构**。每条 state 变更和 Command 必须有源码依据；找不到 route 就如实写「未在 Controller route 中找到映射」，不要编一个看着合理的方法名。
- **忠于当前代码**。代码与架构规范不一致时，按当前实际代码写，并在「备注」里点出违例（例如「Store 直接调用了 Service」），不要美化。
- **只读不改**。本 skill 只产出分析，不改源代码；用户要求一并重构时，先交付分析，再切到 `best-ios` 的 Refactor 模式。
