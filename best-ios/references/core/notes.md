# 注意事项速查

重构 / Review 时常踩的坑与强约束清单，按主题分组。本文件只收录**容易遗漏**或**已在项目中出过问题**的规则，完整架构约束见 `architecture.md`。

***

## 编码规范

- 缩进 **2 空格**
- **一个文件只放一个类 / struct / enum**
- **一个页面一套完整架构**：主工程内每个页面在业务目录下独立建 `<PageName>/` 目录，按层拆 `Entry/ Controllers/ Managers/ Services/ Views/`
- 每个 iOS 项目都有对应的核心 SPM 包（命名约定 `<XxxCore>`）：**Store / Event / Command / Model（Entity / Item / Node）/ Util 必须放进这个包**，不放主工程，并在包内 `Tests/` 覆盖单元测试；包内按 `Store/ Model/ Utils/` 子目录组织（详见 `architecture.md` 的「文件分层与目录结构」）
- **禁止强制解包可选类型**（`!`）；须用 `guard let` / `if let` / `??`
- **禁止** **`try?`**；必须 `do/catch`，`catch` 分支用 `XLogger` 记录错误
- Debug 目录下的文件必须整体置于 `#if DEBUG ... #endif` 内

***

## 并发与单例

- 单例必须是 `actor`，不要用 `class + static let` 或 `@MainActor class`
- Controller、Store 按 `swift-templates.md` 默认标注 `@MainActor`；Manager 默认不标注 `@MainActor`，Manager 主动事件仍由 Controller 在 `bindManagerEvents` 中切回主线程
- Store 是业务数据 + 事件调度的合流点，不要在 `handle(event:)` 里直接起长任务；长任务走 Command → Manager
- Service 建议 `actor`，避免被多个 Manager 并发调用时出现共享状态竞争

***

## Event / Command 约束

- Event 仅描述「发生了什么」，不要把业务判断写进 case 名字
- Command 仅描述「应当做什么」，**只用于驱动 Manager 业务方法或驱动页面跳转**；Store 自身的状态更新在 `handle(event:)` 内直接完成，不要再设计 `set*` 风格的 Command
- Event 遵循 `EventType`，Command 遵循 `CommandType`，由协议暴露日志所需的稳定名称与结构化 payload；不要让它们继承 `Codable` / `Encodable` / `Decodable`
- 跳转类 Command（`pushDetail` / `presentSheet` / `dismiss` 等）由 Controller 在编排函数中调用 Page / ViewController 注入的跳转回调触发；Controller 不直接持有 `UIViewController` / `UINavigationController`，Store 不感知任何 UI 容器与跳转 API
- Store 单个 Event 处理路径如果需要产出多个 Command，必须先组装 `[Command]`，再通过统一派发入口一次性输出；空数组不派发
- Store 的 Command 出口必须是 `AsyncStream<[Command]>`；Controller 持有 `commandTask` 用 `for await` 顺序消费，并在 `deinit` 中取消
- **不要**在同一个 Store `handle(event:)` 方法或分支里多次 `dispatch(commands:)` / `continuation.yield(...)` 逐条派发 Command
- **不要**回退到 `PassthroughSubject<[Command], Never>` / `AnyPublisher<[Command], Never>` 作为 Store 命令出口
- Store 必须通过 `XLoggerStoreReporter<Event, Command>` 上报事件流；不得回退到 `XLogger.event(...)` 散点直写或自建 reporter
- `handle(event:)` 进入时必须清空 `pendingReportedCommands`，事件处理结束后调用 `reporter.dispatch(event:commands:)` 一次性上报 event + 同批 commands，再复位 pending；不得逐条上报，也不得只上报 event 不带 commands
- `dispatch(commands:)` 必须把当前事件链路产生的命令累积到 `pendingReportedCommands`，由 `handle(event:)` 末尾统一上报
- 任何绕过 `handle(event:)` 直接调用 `dispatch(commands:)` 的历史兼容路径，必须加隔离标记，避免旁路命令污染下一次 Event 上报 group
- Store 必须暴露 `nonisolated static let xloggerStoreName: String` 作为远端事件流的稳定标识，默认 `init` 用它构造 `XLoggerStoreReporter`，另提供 `init(reporter:)` 重载用于测试注入
- **不要**在 Store / Manager 里互相引用；Store 不持有 Manager，Manager 也不持有 Store，全部通过 Controller 编排
- **不要**让 Manager 引用、持有、初始化或直接调用其他 Manager；跨 Manager 业务串联必须走 Event → Store → Command → Controller → 调用对应 Manager 业务方法 → 返回值转 Event 投回 Store
- **不要**由 View / Store 直接调用 Manager 的业务方法；Manager 业务方法**只能**由 Controller 的编排函数（每个 Command 对应的 private 方法）调用
- Manager **不订阅 Command**：Command 由 Controller 在 `route(_:)` 中接住，再调用对应 Manager 业务方法；Manager 业务方法返回的是**业务数据**（Item / 业务值），不是 `[Event]`，由 Controller 转 Event 投回 Store
- Manager / Service 对外接口与内部协作都不叠加 Event/Command：Controller 调 Manager、Manager 调 Service、Service 之间协作都用普通函数签名——同步方法直接返回结果，异步方法用 `async`（必要时 `async throws`）；Event/Command 只用于「Store ↔ Controller」之间的调度边界
- Manager 的 `eventPublisher` 仅承载**与具体 Command 无关的主动事件**（系统回调、长轮询、外部通知），由 Controller 的 `bindManagerEvents` 订阅

***

## 分层依赖常见违规

| 违规                                        | 正确做法                                     |
| ----------------------------------------- | ---------------------------------------- |
| View 持有 Manager / Service                 | View 只依赖 Store State；交互通过 `onEvent` 回调上报 |
| Store 依赖 Service / Manager                | Store 只做 Event 调度 + State 计算 + 持有 Item；业务执行放 Manager |
| Store 把自身状态变更包装成 Command            | 状态更新在 `handle(event:)` 的处理函数内**直接完成**；Command **只用于驱动 Manager 业务方法或驱动页面跳转** |
| Controller 直接持有 / 调用 `UIViewController` / `UINavigationController` 做跳转 | Controller 通过 `init` 注入的跳转回调（`onPushDetail` / `onPresentSheet` / `onDismiss`）触发跳转；UI 容器由 Page / ViewController 自己持有 |
| Page / ViewController 在生命周期里直接调 `manager.xxx()` / 自己写业务跳转判断 | Page / ViewController 只负责注入跳转回调与在回调闭包内执行 push / present / dismiss / pop；业务判断收敛在 Store，跳转决策通过 Command 输出 |
| 跳转所需的 Item / 标识符放在 Controller / View 临时变量里 | 跳转参数随跳转 Command 的 payload 一起从 Store 输出（或由 Controller 编排函数在 Store 当前状态中取得后传入回调） |
| Store 单次处理多次 `dispatch(commands:)` / `continuation.yield(...)` | 先组装 `[Command]`，再通过统一派发入口一次性输出给 Controller |
| Store 暴露 `commandPublisher` / `PassthroughSubject<[Command], Never>` | Store 暴露 `commands: AsyncStream<[Command]>`，Controller 用 `commandTask` 消费 |
| Manager 持有 UIKit / SwiftUI 类型             | Manager 只依赖 Service / Model              |
| Manager 引用 / 调用另一个 Manager              | 跨 Manager 协作走 Event → Store → Command → Controller → 调用对应 Manager；共享能力下沉 Service / Util |
| Manager 订阅 Command 或返回 `[Event]`       | Manager 业务方法是普通函数签名，返回**业务数据**；由 Controller 在编排函数里调用，再把返回值转 Event 投回 Store |
| Controller 遵循 `ObservableObject`          | Controller 是普通 `class`，State 只在 Store 里  |
| Controller 在 `route(_:)` 里加业务 `if`     | `route(_:)` 只做 switch + 调用对应 private 编排函数；业务判断放 Store 的 `handle(event:)`，编排细节放编排函数 |
| Controller 的每个编排函数内部再创建 `Task`      | `route(_:) async` 统一异步边界，按 Command 顺序 `await` 编排函数 |
| View / Store 直接调用 `manager.xxx()` 业务方法 | Manager 业务方法**只能**由 Controller 的编排函数调用；UI 交互走 Event → Store → Command → Controller |
| 把 Item 存在 Controller / Manager / View 里   | Item 由 Store 统一持有，视图层只消费 Store 暴露的 Node  |
| Service 一个类处理多种业务                         | 一种业务一个 Service，按职责拆分                     |
| Manager / Service 内部直接写大段纯同步的数据加工 / 转换 / 过滤 / 聚合 / 计算 / 规则判定逻辑 | 抽到对应 Util 静态方法（纯函数式接口，无副作用、无状态），由 Util 补单测覆盖；Manager / Service 内只调用 Util |

***

## Util

- **Util 不只是常用方法 / 常量集合**，它是项目里所有**纯同步数据处理逻辑**的承载层：转换、过滤、聚合、计算、规则判定、格式化等同步逻辑都应抽到合适的 Util
- Manager / Service 内一旦出现「不依赖外部 I/O、只对入参做加工得出结果」的同步代码块，就应该抽到对应 Util，再由 Manager / Service 调用；Manager / Service 自身只保留调度、I/O、组装
- Util 只暴露**纯函数式接口**：给定输入即得稳定输出，无副作用、不持有状态、不依赖单例
- Util 只能依赖系统库、Model、Util，**不得依赖** Service / Manager / Store / Controller / View / 任何 UI 组件
- Util 必须放在核心 SPM 包（`<XxxCore>`）内，并配套单元测试（这是 Util 存在的核心理由——把可单测的纯逻辑从 Manager / Service 里剥出来）
- 命名以 `XxxUtil` 结尾（例如 `TimelineSortUtil`、`AssetGroupingUtil`）

***

## 模型三层

- **Entity** 只存在于数据库层；不要把 `@Model` 类型传到 Store / View
- **Entity** 的形态由持久化技术决定，默认尽量使用 `struct`；只有 SwiftData `@Model` 等框架明确要求引用类型时，才使用 `final class`
- **Item** 必须是 `struct`，由 **Store** 统一持有作为业务数据源；Service 组装时也会使用；不要持有 Entity 引用，不要因为 Event / Command 或日志上报反向要求 Item 遵循编码协议，日志 payload 只暴露必要的标识符 / 展示字段
- **Node** 必须是 `struct` + `Hashable` + `Identifiable`，**禁止包含业务逻辑**；作为 Store 的 `@Published` 属性暴露给视图
- 转换链严格单向：`Entity.toItem() → Item.toNode()`，反向转换不允许

***

## 测试

- 测试框架用 **Swift Testing**（`import Testing` + `@Test`），不要混用 XCTest
- 单元测试（核心 SPM 包 `<XxxCore>`）：**Store**（Event→Command 批次调度、Event→State 状态计算）、**Util**、Node/Item 中的逻辑
- 集成测试（`integration-tests`）：**Manager**、**Service**
- Page、Controller 不写测试
- Store 的 `handle(event:)` 是纯业务调度逻辑，测试最便宜，优先覆盖

***

## SwiftUI / UIKit

- 优先选 SwiftUI；需要 UIKit 时遵循现有 View 组织结构
- UIKit 加 SwiftUI Preview 时，辅助类参考 `../Packages/Base/Sources/SwUI/SwUIPreview.swift`
- 注意 Dark Mode 适配
- `@StateObject` 只在 Page/Root View 创建 Store；子 View 用 `@ObservedObject`

***

## Review 模式专项提醒

Review 时按以下顺序扫描，命中一条即记入清单：

1. Event → Command 批次 / Event → State 的调度是否集中在 Store 的 `handle(event:)` 内？`handle(event:)` 是否只做 switch + 调用 private 处理函数，每个 Event 是否都对应一个 private 处理函数？有没有散落到 Controller / View？
2. Store 是否持有 Item 作为业务数据源？有没有把 Item 放到 Controller / Manager / View？
3. Store 是否把同一处理路径的多个 Command 打包成数组统一派发？有没有在同一方法或分支里多次 `dispatch(commands:)` / `continuation.yield(...)`？是否把自身状态更新错误地包装成了 Command？
3.1 Store 命令出口是否是 `commands: AsyncStream<[Command]>`？有没有残留 `commandPublisher`、`PassthroughSubject<[Command], Never>` 或 `AnyPublisher<[Command], Never>` 作为 Store 命令出口？
3.2 Store 是否注入了 `XLoggerStoreReporter<Event, Command>`？`handle(event:)` 进入时是否清空 `pendingReportedCommands`、结束时是否一次性 `reporter.dispatch(event:commands:)`？`dispatch(commands:)` 是否把命令累积到 `pendingReportedCommands`，而不是"一发就忘"？是否暴露 `nonisolated static let xloggerStoreName`？有没有历史兼容方法绕过 `handle(event:)` 直接 `dispatch` 而未做隔离标记？
4. Manager 业务方法是否**只由 Controller 的编排函数调用**？有没有被 View / Store 直接调用？Manager 业务方法是否以普通函数签名暴露并返回**业务数据**（不是 `[Event]`）？
5. Manager 是否持有、初始化或调用了其他 Manager？跨 Manager 串联是否经由 Event → Store → Command → Controller → 调用对应 Manager → 返回值转 Event 投回 Store？
6. Event / Command 是否都是带 payload 的 enum，分别遵循 `EventType` / `CommandType`，且语义分别只描述「发生了什么」与「应当做什么」？Command 是否只包含「驱动 Manager 业务方法」或「驱动页面跳转」两类 case，没有 `set*` 风格的状态变更 Command？
6.1 Manager / Service 对外接口与内部协作是否还在用 Event/Command 自驱？正确写法是同步方法直接返回结果，异步方法用 `async` / `async throws` 返回结果；Event/Command 只在 Store ↔ Controller 之间使用。
6.2 Manager 的 `eventPublisher` 是否只承载与具体 Command 无关的主动事件？Controller 是否通过 `bindManagerEvents` 订阅并 `.receive(on: DispatchQueue.main)`？
6.3 Manager / Service 内是否还残留大段纯同步的数据加工 / 转换 / 过滤 / 聚合 / 计算 / 规则判定逻辑？这类逻辑是否已经抽到对应 Util（纯函数式接口、无副作用、无状态、放在核心 SPM 包内并补单测）？Manager / Service 自身是否只剩调度、I/O、组装？
7. View 里有没有出现 `Manager` / `Service` 的类型名？
8. Controller 有没有 `: ObservableObject` 或 `@Published` 属性？是否持有 `commandTask` 消费 Store 的 `AsyncStream` 并在 `deinit` 取消？`route(_:) async` 是否只做 switch + 调用 private 编排函数（每个 Command 一个，覆盖业务类与跳转类 Command）？业务类编排函数里是否直接 `await` Manager 并把返回值转 Event 投回 Store？跳转类编排函数里是否只调用注入的跳转回调，没有直接持有 / 操作 `UIViewController` / `UINavigationController`？有没有在编排函数内部再创建二次 `Task`？
8.1 Page / ViewController 是否在初始化 Controller 时显式注入了所有跳转回调？跳转回调闭包是否用 `[weak self]` 捕获、并仅在闭包内执行 push / present / dismiss / pop？跳转状态（`UINavigationController` / `NavigationPath` / sheet binding）是否完全由 Page / ViewController 自己持有，没有泄漏到 Store？
9. 有没有文件放了多个顶层类型？有没有 `try?` 或 `!`？
10. Debug 代码是否包在 `#if DEBUG` 内？
11. 单例是不是 `actor`？
12. 页面是否在业务目录下独立成 `<PageName>/` 目录并按 `Entry/ Controllers/ Managers/ Services/ Views/` 拆分？Store / Event / Command / Model / Util 是否放进核心 SPM 包（`<XxxCore>`）的 `Store/ Model/ Utils/` 子目录，有没有错放在主工程里？
