# iOS 分层架构规范

本文件定义重构所依据的架构规则。执行重构前通读本文件，确认目标结构符合以下约束。

---

## 架构层级规范

### 各层职责

| 类型 | 职责 | 约束 |
|------|------|------|
| **Page** (SwiftUI) / **ViewController** (UIKit) | 页面主入口 | 持有对应的 Controller 和 ContentView；在初始化时为 Controller 注入页面跳转回调（push / present / dismiss / pop 等），并在回调闭包中执行实际跳转动作 |
| **Controller** | 页面逻辑控制层 | 持有对应的 Manager、Store；将 ContentView 上报的 Event 转发给 Store；订阅 Store 输出的 Command 批次后，在 `route(_:)` 内按 Command 调用对应的 private 编排函数，由编排函数直接调用 Manager 业务方法或触发页面跳转回调，并把返回值（如有）转 Event 投回 Store；对外通过可注入的跳转回调（如 `onPushDetail`、`onPresentSheet`、`onDismiss` 等）暴露页面跳转能力，自身不直接持有/操作 UIViewController/UINavigationController；同时订阅 Manager 的 `eventPublisher`（仅承载与具体 Command 无关的主动事件），切回主线程后投回 Store |
| **Manager** | 业务逻辑管理层 | 业务方法只由 Controller 的编排函数（每个 Command 对应一个 private 方法）直接调用，禁止被 View / Store 直接调用；业务方法以普通函数签名暴露，同步直接返回结果，异步用 `async`（必要时 `async throws`），返回的是**业务数据**（Item / 业务值），**不是 Event**；可依赖不同 Service、Util；不得引用、持有、初始化或直接调用其他 Manager；不能依赖任何 UI 组件类；`eventPublisher` 仅用于推送**与具体 Command 无关的主动事件**（系统回调、长轮询、外部通知）；**Manager 内部对 Service 的调用同样走普通函数签名，不复用 Event/Command**；**Manager 内一切纯同步的数据加工 / 转换 / 过滤 / 聚合 / 计算逻辑都应抽到对应 Util，由 Util 承载并补单测，Manager 只负责调度** |
| **Service** | 服务层（网络、缓存、存储等） | **Service 类型必须声明为 `class`（`final class XxxService`），不允许用 `struct` / `enum` / `actor` 承载；且不要求遵守 `Sendable`**；每种 Service 只能处理一种业务逻辑；可依赖 Model、Util；**Service 对外是普通函数接口，不参与 Event/Command 调度，同步方法直接返回结果，异步方法用 `async` 返回结果**；**Service 内一切纯同步的数据加工 / 转换 / 过滤 / 聚合 / 计算逻辑都应抽到对应 Util，由 Util 承载并补单测，Service 只负责 I/O 调度与组装** |
| **Store** | 业务数据处理层 / 事件调度层 | 持有 Item（业务模型）作为数据源；`handle(event:)` 是 Event 唯一入口，只做 switch + 调用对应的 private 处理函数；状态更新（`@Published` 属性）在处理函数内**直接完成**，不经过 Command；Command 批次**用于驱动 Manager 业务方法或驱动页面跳转**（统一由 Controller 路由），单个 Event 处理路径若需要多个 Command，必须先组装 `[Command]` 后通过统一派发入口一次性输出；继承 ObservableObject，通过 `@Published` 属性（Node 为主）驱动 UI 刷新；可依赖 Util；不能依赖 Service / Manager；不感知任何 UI 容器与跳转 API |
| **View** | UI 组件层 | 只负责渲染 UI；不能依赖 Manager / Service；可依赖 Model 驱动渲染；交互通过 Event 上报到 Controller |
| **Model** | 数据模型层 | **类型名必须带明确的 `Entity` / `Item` / `Node` 后缀**（`<业务名>Entity` / `<业务名>Item` / `<业务名>Node`），禁止 `Model` / `Data` / `Info` / `DTO` / `VO` 等其他后缀或无后缀命名；不能依赖任何服务、数据、管理类；只能依赖 Util |
| **Util** | 工具类 / 纯同步数据处理层（常用方法、常量、数据加工、转换、过滤、聚合、计算等同步逻辑） | **Util 类型必须声明为 `struct`，不允许用 `enum` 承载**；只能依赖系统库；所有 Manager、Service 中纯同步的数据处理逻辑都应抽到合适的 Util 单独承载，便于单测覆盖；只暴露纯函数式接口（无副作用、无外部依赖、给定输入即得稳定输出），不持有任何状态 |

### 标准依赖架构

```
Page / ViewController  ──注入跳转回调──▶  Controller
  ▲                                        │
  │                                        │
  │ 跳转回调触发 (push/present/dismiss)     │
  │◀───────────────────────────────────────┤
  │
  ├── Controller
  │     ├── Store     ──[Command] 批次──▶  Controller.route ──┬──▶  Manager 业务方法
  │     │                                                    └──▶  调用页面跳转回调 ──▶ Page/ViewController 执行跳转
  │     └── Manager   ──返回业务数据──▶  Controller ──Event──▶  Store
  │                   Manager.eventPublisher ──主动事件──▶  Controller ──Event──▶ Store
  │                   Manager ──▶ Service ──▶ Model
  └── ContentView
        ├── ◀── Store     (State 驱动渲染)
        └── ──Event──▶ Controller ──▶ Store
```

- Store 与 Manager **彼此不持有引用**，全部由 Controller 编排
- Manager 业务方法**只由 Controller 的编排函数（每个 Command 对应一个 private 方法）直接调用**；不允许被 Store / View 直接调用，也不订阅 Command
- Manager 与 Manager 之间 **不能互相持有引用**，也不能互相初始化或直接调用；多 Manager 协作必须由 Controller 根据 Store 输出的 Command 编排
- 多个 Manager 需要复用的底层能力必须下沉到 Service / Util，不跨 Manager 调用
- Manager / Service 内一切纯同步的数据加工逻辑（转换、过滤、聚合、计算、规则判定等）都必须抽到对应 Util，由 Util 承载并补单测；Manager / Service 自身只保留调度、I/O 与组装职责
- **Util 类型一律声明为 `struct`**（如 `struct XxxUtil { static func ... }`），不允许用 `enum XxxUtil` 这种「无 case 的命名空间 enum」写法承载工具方法；Util 不持有状态，方法以 `static` 暴露
- Store 是事件调度与业务数据的统一归口：Event 进入 Store，Store 内部要么**直接更新 `@Published` 状态**，要么**产出 Command 批次驱动 Manager 或驱动页面跳转**；状态更新不经过 Command
- 单个 Store `handle(event:)` 处理方法或分支如果需要产出多个 Command，必须先组装 `[Command]`，再通过统一派发入口一次性输出；禁止在同一处理路径中多次逐条派发 Command
- Manager 业务方法执行完成后，**直接以业务数据返回给 Controller**；Controller 拿到返回值后，再通过 `store.handle(event:)` 把结果转 Event 投回 Store
- 页面跳转 Command 由 Controller 在 `route(_:)` 内调用注入的跳转回调（如 `onPushDetail`、`onPresentSheet`、`onDismiss`）触发，由 Page / ViewController 在回调闭包内执行实际的 push / present / dismiss / pop；Controller 不直接持有 UIViewController/UINavigationController，Store 不感知任何 UI 容器与跳转 API
- 页面跳转回调由 Page / ViewController 在初始化 Controller 时注入；跳转所需的参数（目标页所需的 Item / Node / 标识符等）由 Controller 从 Store 当前状态或 Command payload 取得后传给回调
- Manager 的 `eventPublisher` 仅承载**与具体 Command 无关的主动事件**（系统回调、长轮询、外部通知），由 Controller 的 `bindManagerEvents` 订阅并切回主线程后投回 Store
- ContentView 的渲染由 Store 提供的 State **直接驱动**
- Controller 不应该遵循 ObservableObject

---

## 文件分层与目录结构

### 以页面为单位划分一套完整架构

- **一个页面 = 一套完整架构**：每个页面独立拥有自己的 Page/ViewController、Controller、Manager、Service、View、Store、Event、Command、Model、Util，不与其他页面混放
- 主工程内每个页面在业务目录下建立 `<PageName>/` 独立目录（父目录沿用所在项目既有约定，如 `Bizs/` / `Modules/` / `Features/`），按层拆分子目录：

```
<业务目录>/<PageName>/
  Entry/        — Page（SwiftUI）/ ViewController（UIKit）入口，可含 +Alert 等 extension 拆分文件
  Controllers/  — Controller
  Managers/     — Manager
  Services/     — Service
  Views/        — View；可再分 Cells/ Components/ SwiftUI/ 等子目录
```

> 同一页面的所有层都收敛在该页面目录下，不跨页面共享文件。

### Store / Model / Util 必须放进 SPM 包

- **Store、Event、Command、Model（Entity / Item / Node）、Util 一律不放主工程**，必须放进当前 iOS 项目对应的核心 Swift Package（命名约定 `<XxxCore>`，如 `AppCore` / `<ProjectName>Core`），并在包内配套单元测试
- 包内按类型拆分子目录：

```
Packages/<XxxCore>/Sources/<XxxCore>/
  Store/   — Store、Event、Command（同一页面的 <Page>Store / <Page>Event / <Page>Command 各自独立文件）
  Model/   — Entity / Item / Node
  Utils/   — Util（纯同步数据处理逻辑，命名 XxxUtil，类型声明为 struct）
```

- 对应单元测试放在 `Packages/<XxxCore>/Tests/<XxxCore>Tests/` 下，按 `Store/` / `Utils/` 等同名子目录组织
- 这样划分的核心目的：把可单测的纯逻辑（Store 调度、Util 数据处理、Model 内逻辑）从主工程里剥离到 SPM 包，使其脱离 App 构建即可独立编译与测试

---

## 模型设计规范

### 三层模型

```
Entity  →  Item  →  Node
(持久层)  (业务层)  (视图层)
```

| 层级 | 命名示例 | 使用场景 | 持有者 |
|------|---------|---------|--------|
| **Entity** | `ProjectEntity` | 数据库业务，SwiftData 模型 | Service / 数据库层 |
| **Item** | `ProjectItem` | Service 层与 Store 层业务逻辑 | Store（作为业务数据源） / Service |
| **Node** | `ProjectNode` | Store 对外暴露给 View 的渲染状态 | Store 的 `@Published` 属性 |

**转换链**：`Entity.toItem()` → `Item.toNode()`

### 模型命名要求

- **Model 类型名必须带明确的 `Entity` / `Item` / `Node` 后缀**，即 `<业务名>Entity`、`<业务名>Item`、`<业务名>Node`；从名字就能读出它属于持久层、业务层还是视图层
- 三层同源模型必须共用同一个业务名前缀，仅后缀不同（如 `ProjectEntity` / `ProjectItem` / `ProjectNode`），不允许同一业务在不同层用不同前缀
- 禁止无后缀或自造后缀的模型命名，如 `Project`、`ProjectModel`、`ProjectData`、`ProjectInfo`、`ProjectDTO`、`ProjectVO`、`ProjectViewModel` 等；已有此类命名的模型必须重命名到对应后缀
- 后缀必须与实际职责一致：被 Service / 数据库层持有的持久化模型用 `Entity`，Service 与 Store 之间流转的业务模型用 `Item`，Store 通过 `@Published` 暴露给 View 渲染的用 `Node`；不允许用 `Node` 命名却承载业务逻辑，或用 `Item` 命名却直接绑定到 View
- 该命名要求只约束三层模型本身；Event / Command（enum）、Util（`struct XxxUtil`）、请求参数或配置类型等不属于 Model 层，不套用这三个后缀

### 模型设计要求

- **Node** 必须是 `struct`，实现 `Hashable` + `Identifiable`，只包含展示字段，无业务逻辑
- **Item** 是 `class`（引用类型），持有业务逻辑，可持有 Entity 引用用于写回数据库；由 Store 统一持有与管理
- **Entity** 遵循对应数据库框架的规范（如 SwiftData 的 `@Model`）

---

## 数据流设计

- **Event** 与 **Command** 均设计成带 payload 的 enum，分别表示「发生了什么」与「应当做什么」，且必须遵循 `Codable`，以便调试、回放、序列化
- **入口**：所有 UI 交互、Manager 返回结果都以 Event 形式经由 Controller 传入 Store
- **调度**：Store 接收 Event 后，根据当前业务语义与持有的 Item 数据，选择：
  - 直接计算新状态 → 更新 `@Published` 属性（Node）→ ContentView 自动刷新
  - 或产出 Command 批次（例如需要异步业务执行 / 需要触发页面跳转），交由 Controller 路由
- **路由**：Controller 订阅 Store 的 Command 批次流，在 `route(_:)` 内按 Command 调用对应的 private 编排函数；`route` 只做 switch，不掺入业务判断
- **执行（业务类 Command）**：Controller 的编排函数**直接调用 Manager 的业务方法**（普通函数签名，必要时 `async`），拿到 Manager 返回的**业务数据**后，再通过 `store.handle(event:)` 把结果转 Event 投回 Store
- **执行（跳转类 Command）**：Controller 的编排函数调用 Page / ViewController 注入的跳转回调（如 `onPushDetail`、`onPresentSheet`、`onDismiss`），由 Page / ViewController 在回调闭包内执行 push / present / dismiss / pop；跳转完成后若需回写状态，再走 Event 投回 Store
- **Manager 主动事件**：与具体 Command 无关的事件（系统回调、长轮询、外部通知）通过 Manager 的 `eventPublisher` 推送，由 Controller 的 `bindManagerEvents` 订阅并切回主线程后投回 Store
- **Manager / Service 内部不沿用 Event/Command**：Manager 调用 Service，以及 Service 之间的协作，使用普通函数签名——同步方法直接返回结果，异步方法用 `async`（必要时 `async throws`）返回结果；Event/Command 只用于「Store ↔ Controller」之间的调度边界，Controller ↔ Manager 是普通函数调用
- **闭环（业务）**：UI Event → Store → (Command → Controller 调用 Manager → 返回业务数据 → Controller 转 Event) → Store → @Published 更新 → View 刷新，形成单向数据流
- **闭环（跳转）**：UI Event → Store → (跳转 Command → Controller 调用注入的跳转回调 → Page / ViewController 执行实际跳转)；如跳转结果需要回写业务状态，由发起方或目标页通过 Event 投回 Store

---

## 单元测试规范

- **需要单元测试**：Store（Event → Command 批次 / Event → State 的调度与状态计算逻辑）、Util；Node 和 Item 中若有逻辑也需覆盖
- **不需要单元测试**：Page、Controller、Manager
