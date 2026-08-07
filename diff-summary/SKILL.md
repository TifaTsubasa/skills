---
name: diff-summary
description: Use when asked to summarize, describe, or review working directory Git changes. Triggers on requests like "summarize my changes", "what did I change", "describe changed files", or similar review requests.
---

# Working Changes Summary

## Overview

Read both the Git staged diff and the unstaged working directory diff, analyze each changed file, and produce one combined summary with five fixed sections:

1. 类依赖变动
2. Event/Command 调整和含义列表
3. Manager / Service 相关功能变动
4. 新增或删除的模型
5. 测试文件改动和测试 Case 简要描述

The output should still distinguish staged changes from unstaged changes inside each section when useful, but the top-level structure must always follow the five sections above.

最终总结**只需要写入 Markdown 文件**，存放到仓库根目录下的 `.codex/diff/` 文件夹（不存在则创建），文件名使用 `changes-YYYYMMDD-HHmm.md`（基于本地时间，**不要以 `diff-summary` 开头**）。聊天里**不要输出五段总结正文**，只回复一行写入结果即可，成功时必须输出 Markdown 文件的绝对路径（例如 `已写入：/Users/yuri/Desktop/workspaces/ios/Photos/.codex/diff/changes-YYYYMMDD-HHmm.md`），失败时简述原因。

## Steps

1. **Get staged diff**
   ```bash
   git diff --cached
   ```
   If empty, also check:
   ```bash
   git diff --cached --name-only
   ```

2. **Get unstaged working directory diff**
   ```bash
   git diff
   ```
   If empty, also check:
   ```bash
   git diff --name-only
   ```

3. **Build one merged view of all changes**

   - Track whether each file is in staged diff, unstaged diff, or both
   - Summarize staged and unstaged changes together under the same five sections
   - When necessary, annotate a file or bullet with `暂存区` / `工作区`
   - **忽略 Markdown 文件**（`*.md` / `*.markdown`）：文档类改动不参与五段总结的任何归纳，也不在任何小节里出现

4. **Section 1: 类依赖变动**

   只要某个**已有类**在本次改动里增加或删除了依赖（构造器注入、`init` 形参、存储属性类型、`@Injected` 之类的属性包装、对单例/工厂的直接持有等），就要单独列出来。Section 4（新增或删除的模型）只覆盖**新增或删除整个类型**的情形；本节关注的是**类型未变、但依赖关系发生增减**的存量类。

   判断依据从 diff 中可见的信号即可：

   - `init(...)` 形参的增删
   - 存储属性、`let` / `var` 声明的新增或移除
   - 通过协议代替具体类型注入（视为依赖被替换：旧依赖删除 + 新依赖新增）
   - 直接 `Singleton.shared` / 工厂调用的引入或删除

   只描述对**行为型类型**（Controller / Manager / Service / Store / Coordinator / Provider 等）的依赖增删；对**模型类型**（`struct` / `enum` / `typealias` 以及仅承载数据或契约的 `protocol` / `class`，参见 Section 4 的模型范畴）的依赖不在本节展开。

   每个类一段，整段包在 ` ```diff ` 代码块里，复用 `+` / `-` 前缀以借用 Markdown 渲染器的红绿高亮。如果被列出的依赖**自身**也在本次 diff 中新增/删除了下层依赖，用缩进继续向下嵌套，形成一棵依赖树：

   ````
   ## 类依赖变动

   ```diff
   + ArrangeMonthController
   +   ArrangeMonthAssetManager
   +     ArrangeMonthListController
   +   ArrangeService

   - LegacyTimelineController
   -   OldDataService

   - SomeController
   -   OldDataService
   + SomeController
   +   NewDataService
   ```
   ````

   规则：

   - 整段必须使用 ` ```diff ` 代码块包裹，使 GitHub / GitLab / VSCode 预览能给 `+` / `-` 行上色
   - `+ ClassName` 表示该类**只新增**了依赖，下面用 `+` 列每个新增依赖（含缩进继续保留 `+` 前缀）
   - `- ClassName` 表示该类**只删除**了依赖，下面用 `-` 列每个被删依赖（含缩进继续保留 `-` 前缀）
   - 同一个类**同时**有新增和删除（例如把具体类型替换为协议）时，拆成相邻两段：先 `- ClassName` 段列删除项，再 `+ ClassName` 段列新增项；不要使用 `~`，diff 高亮不识别
   - 缩进每级 2 空格；嵌套行的开头仍是 `+ ` 或 `- `，再跟空格组成的缩进，避免出现没有 `+`/`-` 前缀的"中性行"
   - 多层嵌套：被列出的依赖如果在同次 diff 里**自身也有依赖增删**，继续在其下方按相同语法缩进展开，最终呈现为一棵依赖树（如上例 Controller → Manager → 子 Controller）
   - 注意分层约束：`Store` 不应依赖 `Manager`，`Manager` 不应依赖 `Controller`，违反分层的依赖在对应描述中以一句话指出（写在 diff 块外的普通段落里）
   - 仅参数顺序调整、命名改写、可见性变化等不算"依赖变动"，不要列入
   - 对模型类型（`struct` / `enum` / `typealias` 等，参见 Section 4）的依赖增减不在本节列出
   - 没有任何依赖变动时，本节写 `- 无依赖变动`（这一行不需要包在 diff 块里）

5. **Section 2: Event/Command 调整和含义列表**

   If any Store `Event` / `Command` cases are added, removed, renamed, or changed, list them explicitly:

   ```
   ## Event/Command 调整和含义列表

   - **path/to/SomeStore.swift**
     - 新增 `Event.loadAssets(source:)`：接收页面加载事件并携带来源信息
     - 删除 `Command.reloadTimeline`：不再由 Controller 触发时间线整页重载
     - 调整 `Command.showDeleteConfirmation(payload:)`：补充弹窗所需上下文
   ```

   Describe each case in terms of its trigger, payload, or side effect.

6. **Section 3: Manager / Service 相关功能变动**

   只列出本次 diff 中 `Manager` / `Service` 类型（或被同名后缀标记的服务层）发生的功能变动，例如对外方法签名、职责拆分/合并、生命周期、并发模型、注入方式等。

   ```
   ## Manager / Service 相关功能变动

   - **path/to/SomeManager.swift**
     - `loadCover(for:)` 改为异步方法，所有调用方需同步迁移
     - 新增 `purgeExpired()` 对外接口，关联持久化清理策略
   ```

   规则：

   - 只覆盖 `Manager` / `Service` 文件本体的功能变动；纯私有实现细节、命名调整、格式化不计
   - 同一个文件内的多条变动按子弹点合并到该文件下
   - 若 Manager / Service 是**新增或删除整个类型**，由 Section 4 覆盖；本节描述的是其内部功能演进
   - 没有任何相关变动时，本节写 `- 无相关改动`

7. **Section 4: 模型新增、删除或修改**

   覆盖本次 diff 中模型层（`struct` / `class` / `enum` / `actor` / `protocol` / `typealias` 等承载数据或契约的类型）的三类变动：**新增整个类型**、**删除整个类型**、**已有类型的属性/case 增删改**。

   ```
   ## 模型新增、删除或修改

   - **path/to/NewType.swift** *(new)*
     - 新增 `NewType`：<一句话描述模型作用 / 表达的领域概念>
     - 属性：
       - `id: UUID`：实例唯一标识
       - `title: String`：列表展示用的标题
       - `assets: [Asset]`：归属本组的资源集合
       - `createdAt: Date`：创建时间，用于排序
     - 引用：被 `CallerA`、`CallerB` 使用；依赖 `DepX`、`DepY`

   - **path/to/OldType.swift** *(deleted)*
     - 删除 `OldType`：<一句话描述被替代或废弃原因>
     - 引用（删除前）：被 `XXX` 持有；依赖 `YYY`

   - **path/to/ExistingType.swift** *(modified)*
     - 调整 `ExistingType`
     - 属性变动：
       - 新增 `coverAssetID: UUID?`：记录主图，渲染封面用
       - 调整 `title: String → String?`：允许空标题以适配草稿态
       - 删除 `legacyIndex: Int`：旧排序字段，已被 `sortKey` 取代
   ```

   规则：

   - **新增模型**：必须用一句话写清模型作用，并在「属性」子项里**列举全部属性**，每条用一句话说明该属性在模型中的作用（不是字段类型的复述）；`enum` 用 `case` 列举，`protocol` 用方法/关联类型列举
   - **删除模型**：写明被替代或废弃原因，并尽量列出删除前的引用关系
   - **修改已有模型**：只列出本次 diff 中**实际被增删改的属性 / case**，每条说明该属性的作用与变动原因（类型变化、可空性变化、语义变化等都要点明）；纯命名调整、可见性变化或只动注释/格式不计
   - 引用关系从 diff 自身能看到的 import、属性、构造器注入、方法签名、工厂或直接调用中归纳
   - 没有任何模型相关变动时，本节写 `- 无相关改动`

8. **Section 5: 测试文件改动和测试 Case 简要描述**

   Only include changed test files:

   ```
   ## 测试文件改动和测试 Case 简要描述

   - **Tests/SomeTest.swift**
     - 新增用例 `foo_handles_empty_input`：验证空输入分支
     - 调整用例 `bar_retries_on_failure`：匹配新的构造参数
   ```

   If a test file changed but no case name is visible, summarize the test intent briefly.

9. **写入 Markdown 文件**

   五段总结组织好后，**只**把完整内容输出到 Markdown 文件，**不要**在聊天里复述：

   - 目录：仓库根目录下 `.codex/diff/`，不存在时先创建
   - 文件名：`changes-YYYYMMDD-HHmm.md`（本地时间，同分钟内重复生成则覆盖）。**禁止**使用 `diff-summary` 作为文件名前缀
   - 内容：完整的五段式总结，文件开头加一级标题 `# Diff Summary` 和一行 `生成时间：YYYY-MM-DD HH:mm` 作为前言
   - 聊天回答：只回复一行写入结果，成功时必须输出 Markdown 文件的绝对路径，例如 `已写入：/Users/yuri/Desktop/workspaces/ios/Photos/.codex/diff/changes-YYYYMMDD-HHmm.md`；写入失败时简述失败原因。不要附带任何总结正文、节标题或解释

## Output Format & Example

输出格式骨架与"月份页资源管理重构"完整示例放在 `references/output-example.md`，生成最终回答前先读这份文件对照格式与颗粒度，不要把示例本身作为答案输出。

## Rules

- Write the summary in the same language the user used.
- **聊天回答只输出一行写入结果**（成功时给出 Markdown 文件绝对路径，失败时给出原因）；不要把五段总结正文、节标题、diff、代码块或原始 patch 文本贴回聊天。
- Always check and summarize both `git diff --cached` and `git diff`.
- Markdown 文件（`*.md` / `*.markdown`）一律忽略，不进入任何小节，也不在写入文件中提及。
- Keep the output in exactly five top-level sections in the order defined above.
- If a section has no content, state that directly under that section heading, such as `- 无相关改动`；类依赖变动段为空时写 `- 无依赖变动`。
- If a file has only trivial whitespace changes, note it as `格式调整`，不要单独列入。
- If `Event` / `Command` exists in the diff, always list the designed cases explicitly.
- For Section 1 (类依赖变动)：只列出**已有类**在依赖关系上的增删；新增/删除整个类型属于 Section 4。仅命名、可见性、参数顺序变化不算依赖变动。**只描述对行为型类型（Controller / Manager / Service / Store 等）的依赖**，对模型类型（struct / enum / typealias / 数据契约 protocol 等）的依赖增减不展开。整段依赖树必须用 ` ```diff ` 代码块包裹，"替换型"类拆成相邻的 `- ClassName` / `+ ClassName` 两段，不要使用 `~` 前缀。
- For Section 3 (Manager / Service 变动)：只覆盖 `Manager` / `Service` 文件本体；其他业务文件（Controller、View、Store 等）不在本节展开。
- For Section 4：覆盖模型的新增、删除和**属性 / case 的增删改**。新增模型必须列出全部属性并逐条说明作用；修改的模型只列出实际变动的属性，并说明每条属性的作用与变动；普通方法/逻辑实现的改动仍不在本节展开。
- For Section 5, include only test files and keep each test case description to one line.
- If both staged and unstaged diffs are empty, all five sections should explicitly state `- 无相关改动`（类依赖变动段写 `- 无依赖变动`）。
- 每次总结都要把最终内容写入 `.codex/diff/changes-YYYYMMDD-HHmm.md`（不存在的目录自行创建），文件名禁止以 `diff-summary` 开头；聊天回答只回复写入结果一行，成功时必须给出 Markdown 文件绝对路径，不要再贴总结正文。
