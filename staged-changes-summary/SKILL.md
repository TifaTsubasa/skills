---
name: staged-changes-summary
description: Use when asked to summarize, describe, or review working directory Git changes. Triggers on requests like "summarize my changes", "what did I change", "describe changed files", or similar review requests.
---

# Working Changes Summary

## Overview

Read both the Git staged diff and the unstaged working directory diff, analyze each changed file, and produce one combined summary with four fixed sections:

1. 改动文件列表和改动点描述
2. Event/Command 调整和含义列表
3. 新增或删除类后的相关引用图
4. 测试文件改动和测试 Case 简要描述

The output should still distinguish staged changes from unstaged changes inside each section when useful, but the top-level structure must always follow the four sections above.

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
   - Summarize staged and unstaged changes together under the same four sections
   - When necessary, annotate a file or bullet with `暂存区` / `工作区`

4. **Section 1: 改动文件列表和改动点描述**

   For each non-test changed file, produce concise bullets:

   ```
   ## 改动文件列表和改动点描述

   - **path/to/file.ext**（工作区）
     - <change point 1>
     - <change point 2>
   ```

   Focus on what changed and why it matters.

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

6. **Section 3: 新增或删除类后的相关引用图**

   Only include files where a class / struct / enum / actor / protocol / typealias was newly added or deleted.

   ```
   ## 新增或删除类后的相关引用图

   - **path/to/NewType.swift** *(new)*
     - 新增 `NewType`：<一句话描述职责>
     - 引用图：
       - 被 `CallerA`、`CallerB` 依赖（用于 <目的>）
       - 依赖 `DepX`、`DepY` 实现核心逻辑
   ```

   Derive references from the diff itself: imports, properties, constructor injection, function signatures, factory usage, or direct calls visible in the patch.

7. **Section 4: 测试文件改动和测试 Case 简要描述**

   Only include changed test files:

   ```
   ## 测试文件改动和测试 Case 简要描述

   - **Tests/SomeTest.swift**
     - 新增用例 `foo_handles_empty_input`：验证空输入分支
     - 调整用例 `bar_retries_on_failure`：匹配新的构造参数
   ```

   If a test file changed but no case name is visible, summarize the test intent briefly.

## Output Format

```
## 改动文件列表和改动点描述

- **file/path/A.swift**（工作区）
  - 修改了 X 方法签名，增加 `timeout` 参数
  - 移除了废弃的 `legacyFetch()` 调用

- **file/path/B.swift**（暂存区）
  - 新增 `DatabaseUpgradeService` 的接入逻辑

## Event/Command 调整和含义列表

- **file/path/ArrangeStore.swift**
  - 新增 `Event.refreshTriggered`：处理下拉刷新触发
  - 新增 `Event.deleteSelectedItems(ids:)`：接收批量删除交互并携带目标 ID
  - 删除 `Command.reloadTimeline`：不再触发整页重新拉取

## 新增或删除类后的相关引用图

- **file/path/DatabaseUpgradeService.swift** *(new)*
  - 新增 `DatabaseUpgradeService`：负责数据库版本迁移的调度与状态管理
  - 引用图：
    - 被 `AppDelegate` 在启动时调用
    - 依赖 `DatabaseService` 执行实际迁移操作
    - 依赖 `MigrationLogger` 记录升级日志

## 测试文件改动和测试 Case 简要描述

- **Tests/SomeTest.swift**
  - 新增用例 `foo_handles_empty_input`：验证空输入边界值
  - 调整 mock 初始化以匹配新的构造签名
```

## Rules

- Write the summary in the same language the user used.
- Do NOT include diffs, code blocks, or raw patch text in the final answer.
- Always check and summarize both `git diff --cached` and `git diff`.
- Keep the output in exactly four top-level sections in the order defined above.
- If a section has no content, state that directly under that section heading, such as `- 无相关改动`.
- If a file has only trivial whitespace changes, note it as `格式调整`.
- If `Event` / `Command` exists in the diff, always list the designed cases explicitly.
- For Section 1, exclude test files unless the same file also carries important production changes that must be called out there.
- For Section 3, include only added or deleted types; ordinary method edits do not belong there.
- For Section 4, include only test files and keep each test case description to one line.
- If both staged and unstaged diffs are empty, all four sections should explicitly state `- 无相关改动`.
