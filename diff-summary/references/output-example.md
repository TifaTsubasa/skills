# Diff Summary 输出示例

本文件提供 `diff-summary` skill 的两类示例，供生成最终回答前对照：

1. **Output Format**：精简骨架，展示五个 section 的标题与最小结构
2. **Example Output**：基于"月份页资源管理重构"这类真实场景的完整示例，展示真正应有的语气与颗粒度

不要把这些示例本身作为答案输出；它们只是格式参考。

---

## Output Format

````
## 类依赖变动

```diff
+ ArrangeMonthController
+   ArrangeMonthAssetManager
+     ArrangeMonthListController
+   ArrangeService

- LegacyTimelineController
-   OldDataService
```

## Event/Command 调整和含义列表

- **file/path/ArrangeStore.swift**
  - 新增 `Event.refreshTriggered`：处理下拉刷新触发
  - 新增 `Event.deleteSelectedItems(ids:)`：接收批量删除交互并携带目标 ID
  - 删除 `Command.reloadTimeline`：不再触发整页重新拉取

## Manager / Service 相关功能变动

- **file/path/SomeManager.swift**
  - `loadCover(for:)` 改为异步方法，所有调用方需同步迁移
  - 新增 `purgeExpired()` 对外接口，关联持久化清理策略

## 新增或删除的模型

- **file/path/NewModel.swift** *(new)*
  - 新增 `NewModel`：承载 XX 数据
  - 引用：被 `CallerA` 使用；依赖 `DepX`

- **file/path/OldModel.swift** *(deleted)*
  - 删除 `OldModel`：被新批次结构取代
  - 引用（删除前）：被 `XXX` 持有

## 测试文件改动和测试 Case 简要描述

- **Tests/SomeTest.swift**
  - 新增用例 `foo_handles_empty_input`：验证空输入边界值
  - 调整 mock 初始化以匹配新的构造签名
````

---

## Example Output

下面是一个贴近真实场景的完整示例（基于"月份页资源管理重构"这类改动），用于说明各 section 的颗粒度和写法。

````
## 类依赖变动

```diff
+ ArrangeMonthController
+   ArrangeMonthAssetManager
+     ArrangeMonthListController
+     ArrangeFilterReasonResolver
+   ArrangeMonthLoadContext

- ArrangeReloadCoordinator
-   ArrangeMonthController
-   ArrangeReloadStrategy
```

## Event/Command 调整和含义列表

- **Packages/PhotosCore/Sources/PhotosCore/Store/ArrangeMonthStore.swift**
  - 新增 `Command.commitDecisionBatch(payload: ArrangeMonthTaskDecisionPayload)`：按批次落库整理决策，附带用途标记
  - 新增 `Event.assetsScanned(result: ArrangeMonthAssetScanResult)`：扫描完成后驱动 UI 与统计更新
  - 删除 `Command.commitSingleDecision`：单条提交链路废弃，统一走批次
  - 调整 `Event.loadRequested(context:)`：参数由月份对象改为 `ArrangeMonthLoadContext`，附带触发来源

## Manager / Service 相关功能变动

- **Photos/Bizs/Pages/Arrange/Managers/ArrangeMonthAssetManager.swift**
  - `scan(in:)` 返回值由 `[PHAsset]` 改为 `ArrangeMonthAssetScanResult`，包含资源列表、过滤原因和扫描耗时
  - 新增对 `ArrangeFilterReasonResolver` 的注入，把过滤原因判定从 Manager 内部搬出
  - 引入子 Controller `ArrangeMonthListController` 负责列表分段渲染
  - 新增空相册分支的快速返回，避免触发后续整理流水线

- **Packages/PhotosCore/Sources/PhotosCore/Service/ArrangeService.swift**
  - 新增 `purgeExpired()` 对外接口，关联持久化清理策略
  - `loadDecisions(for:)` 改为异步方法，配合 Store 批次命令使用

## 新增或删除的模型

- **Packages/PhotosCore/Sources/PhotosCore/Model/ArrangeMonthAssetScanResult.swift** *(new)*
  - 新增 `ArrangeMonthAssetScanResult`：封装扫描结果（资源、过滤原因、耗时）
  - 引用：被 `ArrangeMonthAssetManager.scan(in:)` 作为返回值产出；被 `ArrangeMonthStore` 在 `Event.assetsScanned` 中消费；依赖 `PHAsset`、`ArrangeFilterReason`

- **Packages/PhotosCore/Sources/PhotosCore/Model/ArrangeMonthLoadContext.swift** *(new)*
  - 新增 `ArrangeMonthLoadContext`：承载月份加载入口的上下文（来源、是否首次、是否带过滤条件）
  - 引用：被 `ArrangeMonthController` 在进入页面时构造并下发；被 `ArrangeMonthStore` 在 `Event.loadRequested` 中消费

- **Photos/Bizs/Pages/Arrange/Controllers/ArrangeReloadCoordinator.swift** *(deleted)*
  - 删除 `ArrangeReloadCoordinator`：原本在 Controller 之上协调整页重载，被 Store 的批次命令链路取代
  - 引用（删除前）：持有 `ArrangeMonthController` 触发整页刷新；依赖 `ArrangeReloadStrategy`；被 `AppRouter` 在进入月份页时构造

## 测试文件改动和测试 Case 简要描述

- **Packages/PhotosCore/Tests/PhotosCoreTests/Store/ArrangeMonthStoreTest.swift**
  - 新增用例 `commitDecisionBatch_persistsAllPayloads`：验证批次命令把整组决策完整下发
  - 新增用例 `loadRequested_withFirstEntryContext_triggersScan`：首次进入上下文应触发扫描
  - 调整用例 `assetsScanned_updatesState`：匹配 `ArrangeMonthAssetScanResult` 新结构

- **Packages/PhotosCore/Tests/PhotosCoreTests/Store/EventCommandCodableTest.swift**
  - 新增 `commitDecisionBatch` 的编解码用例，确保 payload 跨进程传输无丢失
  - 移除已废弃的 `commitSingleDecision` 编解码断言
````
