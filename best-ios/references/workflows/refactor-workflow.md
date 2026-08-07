# Refactor 流程

当用户明确要求「重构 / 调整 / 拆分 / 迁移」代码，需要产出改动时，按以下步骤执行。

## 执行步骤

1. **分析目标模块**
   - 读取 `../core/architecture.md`，对照目标模块当前结构
   - 读取关键文件，理解当前结构
   - 识别哪些类违反了分层约定（如 View 持有 Service、Manager 依赖 Store、Store 依赖 Manager 等）

2. **制定重构计划**
   - 列出需要新建 / 拆分的文件，并明确每个文件的归属目录：页面层（Entry / Controllers / Managers / Services / Views）落在业务目录下的 `<PageName>/`，Store / Event / Command / Model / Util 落在核心 SPM 包 `Packages/<XxxCore>/` 的 `Store/ Model/ Utils/` 子目录（详见 `../core/architecture.md` 的「文件分层与目录结构」）
   - 梳理每层的依赖关系和数据流
   - 确认 Entity → Item → Node 的转换路径，以及 Item 在 Store 中的持有位置
   - 参考 `../core/swift-templates.md` 确认目标代码结构，并把它作为最终代码必须对齐的落地模板

3. **逐步执行重构**
   - 先建立 Model 层（Entity / Item / Node），参考 `../core/swift-templates.md` 的 Model 三层模板
   - 再建立 Service / Manager 层；Manager 业务方法以普通函数签名暴露，返回**业务数据**（不是 `[Event]`），`eventPublisher` 仅承载与具体 Command 无关的主动事件；Manager / Service 内部一切纯同步的数据加工 / 转换 / 过滤 / 聚合 / 计算 / 规则判定逻辑都必须抽到对应 Util（放在核心 SPM 包内，纯函数式接口，配套单元测试），Manager / Service 只保留调度、I/O 与组装
   - 再更新 Store：持有 Item 作为业务数据，`handle(event:)` 只做 switch + 调用 private 处理函数；状态更新在处理函数内直接完成，需要驱动 Manager 或触发页面跳转时通过 `dispatch(commands:)` 输出 `[Command]` 批次；命令出口必须是 `commands: AsyncStream<[Command]>`，并用 continuation 集合管理订阅终止；同时持有 `XLoggerStoreReporter<Event, Command>`（默认 `init` 用 `nonisolated static let xloggerStoreName` 构造，另提供 `init(reporter:)` 重载用于测试注入），`handle(event:)` 入口清空 `pendingReportedCommands`，末尾 `reporter.dispatch(event:commands:)` 一次性上报 event + 同批 commands；`dispatch(commands:)` 内追加 `pendingReportedCommands.append(contentsOf: commands)`；参考 `../core/swift-templates.md` 中的 Event / Command / Store 模板
   - 再更新 Controller（持有 Manager + Store + 跳转回调）：`init` 显式接收所有跳转回调（`onPushDetail` / `onPresentSheet` / `onDismiss` 等）作为闭包参数，Controller 不直接持有 `UIViewController` / `UINavigationController`；`handle(event:)` 仅转发 Event 给 Store；持有 `commandTask` 并用 `for await` 消费 Store 命令流，`deinit` 中取消；`route(_:) async` 只做 switch + 调用 private 编排函数；每个 Command 对应一个 private 编排函数——业务类编排函数**直接调用 Manager 业务方法**并把返回值转 Event 投回 Store，跳转类编排函数**直接调用注入的跳转回调**（必要时从 Store 状态或 Command payload 取参数后传入）；禁止在每个编排函数内部再创建二次 `Task`；`bindManagerEvents` 订阅 Manager 的 `eventPublisher` 并切回主线程
   - 最后更新 Page / ViewController：只依赖 Store 暴露的 Node State，UI 交互通过 `onEvent` 上报；初始化 Controller 时显式注入所有跳转回调，回调闭包用 `[weak self]` 捕获并仅在闭包内执行 push / present / dismiss / pop；UIKit 入口由自身持有 `UINavigationController`，SwiftUI 入口将 `NavigationPath` / sheet binding 等导航状态抽到独立的 `Router`（`@StateObject`）中，绝不放进 Store
   - 每完成一层都要回看 `../core/swift-templates.md`，确保最终产出代码与模板一致，而不是只满足抽象架构概念

4. **验证编译**
   - 对照 `../core/architecture.md` 的依赖约束自查（View 不依赖 Manager/Service、Store 不依赖 Manager 等）
   - 执行编译命令确认无错误
   - 修复所有编译错误后再继续
