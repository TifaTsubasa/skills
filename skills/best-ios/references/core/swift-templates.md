# Swift 分层架构模板

各层完整代码模板，以 `Project` 为示例模块名称。模板严格对齐 `architecture.md` 的依赖约束与数据流。

本文件不是“仅供参考”的示例集合，而是 `best-ios` skill 落地代码时的**强制模板规范**。

- 只要新建、重构或修复 Page / Controller / Manager / Store / Service / View / Model，产出代码都必须与本模板保持一致
- 一致不只指分层名称，还包括职责边界、依赖方向、Event / Command 调度方式、Store 对 Item / Node 的持有关系，以及 Controller / Manager / View 的交互方式
- 若现有实现与本模板冲突，默认应调整实现去贴合模板，而不是为了迁就旧代码去弱化模板约束

---

## Page（SwiftUI 入口）/ ViewController（UIKit 入口）

**强制约束**：

- Page / ViewController 在初始化 Controller 时**必须显式注入跳转回调**（`onPushDetail` / `onPresentSheet` / `onDismiss` 等），跳转动作只在回调闭包中执行
- Page / ViewController 自己持有跳转所需的 UI 容器（`UINavigationController`、SwiftUI `NavigationPath` / sheet binding 等）；Controller 与 Store 都不感知这些容器
- 跳转回调闭包用 `[weak self]` 捕获 ViewController，避免 Controller → 回调 → ViewController 的强引用环

### SwiftUI Page 入口（无跳转的最简版本）

```swift
/// 项目页面入口。
struct ProjectPage: View {
  @StateObject private var store = ProjectStore()
  private let controller: ProjectController

  /// 初始化项目页面并建立 Store 与 Controller。
  init() {
    let store = ProjectStore()
    _store = StateObject(wrappedValue: store)
    controller = ProjectController(
      store: store,
      onPushDetail: { _ in },
      onDismiss: {}
    )
  }

  /// 渲染项目页面内容并转发生命周期事件。
  var body: some View {
    ProjectContentView(
      store: store,
      onEvent: { [controller] event in controller.handle(event: event) }
    )
    .onAppear { controller.handle(event: .viewAppeared) }
    .onDisappear { controller.handle(event: .viewDisappeared) }
  }
}
```

> SwiftUI 入口若需要跳转，将导航状态（`NavigationPath`、`sheet item` 等）抽到 `@StateObject` 持有的 `ProjectRouter` 中，把 `router.pushDetail(_:)` / `router.dismiss()` 作为闭包传给 `ProjectController`，Page 的 `body` 用 `router` 状态驱动 `NavigationStack` / `.sheet`。不要把跳转状态放进 `ProjectStore`。

### UIKit ViewController 入口（含跳转回调）

```swift
/// 项目页面 UIKit 入口。
@MainActor
final class ProjectViewController: UIViewController {
  private let store = ProjectStore()
  private lazy var controller: ProjectController = ProjectController(
    store: store,
    onPushDetail: { [weak self] item in
      let detail = ProjectDetailViewController(item: item)
      self?.navigationController?.pushViewController(detail, animated: true)
    },
    onDismiss: { [weak self] in
      self?.dismiss(animated: true)
    }
  )
  private lazy var hostingController: UIHostingController = UIHostingController(
    rootView: ProjectContentView(
      store: store,
      onEvent: { [unowned self] event in self.controller.handle(event: event) }
    )
  )

  /// 装配 ContentView 并触发首次加载。
  override func viewDidLoad() {
    super.viewDidLoad()
    addChild(hostingController)
    view.addSubview(hostingController.view)
    hostingController.view.frame = view.bounds
    hostingController.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
    hostingController.didMove(toParent: self)
    controller.handle(event: .viewAppeared)
  }
}
```

---

## Controller（编排 Manager / Store / 跳转回调，不遵循 ObservableObject）

**强制约束**：

- `route(_:)` 是 Command 的**唯一分发入口**，只做 `switch` + 调用编排函数；禁止在 `route` 内联调用 `manager` / `databaseManager` / 跳转回调，也不写任何业务判断
- 每个 Command 都必须对应一个 **private 编排函数**，函数名用业务语义动词短语（例如 `fetchItems` / `pushDetail`）
- 业务类 Command 由编排函数直接调用 Manager 业务方法；**跳转类 Command** 由编排函数调用 `init` 注入的跳转回调（`onPushDetail` / `onPresentSheet` / `onDismiss` 等），Controller 自身不持有/操作 `UIViewController` / `UINavigationController`
- 跳转回调的入参（要展示的 `Item` / 标识符等）由编排函数从 Store 当前状态或 Command payload 取得后传入
- Controller 必须持有 `commandTask` 消费 Store 的 `AsyncStream<[Command]>`，并在 `deinit` 中取消任务
- Controller 的编排函数由 `route(_:) async` 顺序调用，禁止在每个编排函数内部再创建二次 `Task`

```swift
/// 项目页面控制层。
/// 负责消费 Store 命令、调用 Manager 或跳转回调，并把业务结果转成 Event 回流 Store。
@MainActor
final class ProjectController {
  private let store: ProjectStore
  private let manager: ProjectManager
  private let onPushDetail: (ProjectItem) -> Void
  private let onDismiss: () -> Void
  private var cancellables = Set<AnyCancellable>()
  private var commandTask: Task<Void, Never>?

  /// 使用项目 Store 与跳转回调初始化控制层并绑定命令与主动事件。
  init(
    store: ProjectStore,
    onPushDetail: @escaping (ProjectItem) -> Void,
    onDismiss: @escaping () -> Void
  ) {
    self.store = store
    self.manager = ProjectManager()
    self.onPushDetail = onPushDetail
    self.onDismiss = onDismiss
    bindStoreCommands()
    bindManagerEvents()
  }

  /// 取消 Store 命令流消费任务。
  deinit {
    commandTask?.cancel()
  }

  // MARK: - Event 入口：Page / View 上报的事件统一从这里进入

  /// 仅做转发：把 UI / 生命周期 Event 投递给 Store；禁止在此写业务判断。
  func handle(event: ProjectEvent) {
    store.handle(event: event)
  }

  // MARK: - Route：唯一的 Command 分发入口

  /// 路由 Store 输出的命令到具体编排函数。
  /// route 只做分发，禁止内联业务逻辑或直接调用 Manager / 跳转回调。
  private func route(_ command: ProjectCommand) async {
    switch command {
    case .fetchItems:
      await fetchItems()
    case .deleteItem(let id):
      await deleteItem(id: id)
    case .pushDetail(let item):
      pushDetail(item: item)
    case .dismiss:
      dismiss()
    }
  }

  // MARK: - 编排函数：每个 Command 对应一个 private 方法

  /// 拉取项目列表，结果以 Event 回流给 Store。
  private func fetchItems() async {
    let items = await manager.fetchItems()
    store.handle(event: .itemsLoaded(items))
  }

  /// 删除指定项目，完成后以 Event 回流给 Store。
  private func deleteItem(id: UUID) async {
    await manager.deleteItem(id: id)
    store.handle(event: .itemDeleted(id: id))
  }

  /// 跳转到详情页，调用 Page / ViewController 注入的跳转回调。
  private func pushDetail(item: ProjectItem) {
    onPushDetail(item)
  }

  /// 关闭当前页面，调用 Page / ViewController 注入的关闭回调。
  private func dismiss() {
    onDismiss()
  }

  // MARK: - 绑定

  /// 绑定 Store 的异步命令流并按批次顺序路由。
  private func bindStoreCommands() {
    let commandStream = store.commands
    commandTask = Task { @MainActor [weak self] in
      for await commands in commandStream {
        guard let self else {
          return
        }

        for command in commands {
          await self.route(command)
        }
      }
    }
  }

  /// 订阅 Manager 的主动事件流（非命令驱动），切回主线程后投回 Store。
  private func bindManagerEvents() {
    manager.eventPublisher
      .receive(on: DispatchQueue.main)
      .sink { [weak self] event in self?.store.handle(event: event) }
      .store(in: &cancellables)
  }
}
```

---

## Event / Command（均为带 payload 的 enum，分别遵循 EventType / CommandType）

> `EventType` / `CommandType` 由日志基础库提供，只表达远端事件流需要的稳定名称与结构化 payload；不要让它们继承 `Codable` / `Encodable` / `Decodable`。

```swift
/// 描述 Store Event 的日志上报契约。
public protocol EventType {
  /// 描述远端日志中的稳定事件名称。
  var eventName: String { get }

  /// 描述远端日志中的事件结构化负载。
  var eventPayload: [String: XLoggerMetadataValue] { get }
}

/// 描述 Store Command 的日志上报契约。
public protocol CommandType {
  /// 描述远端日志中的稳定命令名称。
  var commandName: String { get }

  /// 描述远端日志中的命令结构化负载。
  var commandPayload: XLoggerMetadataValue { get }
}
```

```swift
enum ProjectEvent: EventType {
  case viewAppeared
  case viewDisappeared
  case itemTapped(id: UUID)
  case deleteButtonTapped(id: UUID)
  case closeButtonTapped
  case errorDismissed

  // Manager 回流事件
  case itemsLoaded([ProjectItem])
  case itemDeleted(id: UUID)
  case loadFailed(String)

  /// 描述远端日志中的稳定事件名称。
  var eventName: String {
    switch self {
    case .viewAppeared:
      return "viewAppeared"
    case .viewDisappeared:
      return "viewDisappeared"
    case .itemTapped:
      return "itemTapped"
    case .deleteButtonTapped:
      return "deleteButtonTapped"
    case .closeButtonTapped:
      return "closeButtonTapped"
    case .errorDismissed:
      return "errorDismissed"
    case .itemsLoaded:
      return "itemsLoaded"
    case .itemDeleted:
      return "itemDeleted"
    case .loadFailed:
      return "loadFailed"
    }
  }

  /// 描述远端日志中的事件结构化负载。
  var eventPayload: [String: XLoggerMetadataValue] {
    switch self {
    case .viewAppeared, .viewDisappeared, .closeButtonTapped, .errorDismissed:
      return [:]
    case .itemTapped(let id), .deleteButtonTapped(let id), .itemDeleted(let id):
      return ["id": .string(id.uuidString)]
    case .itemsLoaded(let items):
      return ["count": .int(items.count)]
    case .loadFailed(let message):
      return ["message": .string(message)]
    }
  }
}

enum ProjectCommand: CommandType {
  // 业务类：驱动 Manager 业务方法
  case fetchItems
  case deleteItem(id: UUID)

  // 跳转类：驱动 Page / ViewController 在注入回调中执行跳转
  case pushDetail(item: ProjectItem)
  case dismiss

  /// 描述远端日志中的稳定命令名称。
  var commandName: String {
    switch self {
    case .fetchItems:
      return "fetchItems"
    case .deleteItem:
      return "deleteItem"
    case .pushDetail:
      return "pushDetail"
    case .dismiss:
      return "dismiss"
    }
  }

  /// 描述远端日志中的命令结构化负载。
  var commandPayload: XLoggerMetadataValue {
    switch self {
    case .fetchItems, .dismiss:
      return .object([:])
    case .deleteItem(let id):
      return .object(["id": .string(id.uuidString)])
    case .pushDetail(let item):
      return .object(["id": .string(item.id.uuidString), "title": .string(item.title)])
    }
  }
}
```

---

## Store（持有 Item、调度 Event、产出 Command 批次驱动 Manager 或页面跳转，不依赖 Service / Manager）

**强制约束**：

- `handle(event:)` 是 Event 的**唯一接收入口**，只做 `switch` + 调用对应的 private 处理函数；禁止在 `handle` 内联写状态变更或 `dispatch` 调用
- 每个 Event 都必须对应一个 **private 处理函数**，函数名用业务语义动词短语（例如 `handleViewAppeared` / `applyItemsLoaded`），函数内部完成状态更新与 Command 派发
- Command 输出必须使用 `AsyncStream<[Command]>`，Store 内部用 continuation 集合支持订阅与终止清理
- Store 事件流上报统一使用 `XLoggerStoreReporter<Event, Command>`；`handle(event:)` 进入时清空待上报命令，事件处理结束后一次性上报 event + 同批 commands
- `dispatch(commands:)` 只负责一次性输出 Command 批次，并把当前事件链路产生的命令追加到待上报批次；禁止回退到 `PassthroughSubject` / `AnyPublisher` 作为 Store 命令出口
- 如历史兼容方法会绕过 `handle(event:)` 直接调用 `dispatch(commands:)`，必须增加隔离标记，避免直接派发的命令污染下一次 Event 上报 group

```swift
/// 项目页面状态存储。
/// 负责持有业务 Item、处理 Event、更新 Node 状态并输出 Command 批次。
@MainActor
final class ProjectStore: ObservableObject {
  // 视图状态：@Published Node，驱动 ContentView 渲染
  @Published private(set) var nodes: [ProjectNode] = []
  @Published private(set) var isLoading = false
  @Published private(set) var errorMessage: String?

  // 业务数据源：Item，由 Store 统一持有
  private var items: [ProjectItem] = []

  // Command 批次异步流：Controller 订阅后按顺序路由到 Manager
  private var commandContinuations: [UUID: AsyncStream<[ProjectCommand]>.Continuation] = [:]
  // Store 事件流与命令流远端上报器
  private let reporter: XLoggerStoreReporter<ProjectEvent, ProjectCommand>
  // 当前 Event 处理链路中积累的待上报命令
  private var pendingReportedCommands: [ProjectCommand] = []
  var commands: AsyncStream<[ProjectCommand]> {
    AsyncStream { continuation in
      let id = UUID()
      commandContinuations[id] = continuation
      continuation.onTermination = { [weak self] _ in
        Task { @MainActor in
          self?.commandContinuations[id] = nil
        }
      }
    }
  }

  /// 使用默认事件流上报器初始化项目 Store。
  init() {
    self.reporter = XLoggerStoreReporter(storeName: Self.xloggerStoreName)
  }

  /// 使用指定事件流上报器初始化项目 Store，便于单元测试注入记录器。
  init(reporter: XLoggerStoreReporter<ProjectEvent, ProjectCommand>) {
    self.reporter = reporter
  }

  // MARK: - Event 入口：只做分发，禁止内联状态变更或 dispatch

  /// 处理项目页面事件，并在事件处理结束后上报 event 与同批命令。
  func handle(event: ProjectEvent) {
    pendingReportedCommands = []

    switch event {
    case .viewAppeared:
      handleViewAppeared()
    case .viewDisappeared:
      handleViewDisappeared()
    case .itemTapped(let id):
      handleItemTapped(id: id)
    case .deleteButtonTapped(let id):
      handleDeleteButtonTapped(id: id)
    case .closeButtonTapped:
      handleCloseButtonTapped()
    case .itemsLoaded(let loaded):
      applyItemsLoaded(loaded)
    case .itemDeleted(let id):
      applyItemDeleted(id: id)
    case .loadFailed(let message):
      applyLoadFailed(message: message)
    case .errorDismissed:
      applyErrorDismissed()
    }

    reporter.dispatch(event: event, commands: pendingReportedCommands)
    pendingReportedCommands = []
  }

  // MARK: - Event 处理函数：每个 Event 对应一个 private 方法

  /// 视图首次出现，进入加载态并请求拉取列表。
  private func handleViewAppeared() {
    isLoading = true
    errorMessage = nil
    dispatch(commands: [.fetchItems])
  }

  /// 视图消失，当前无副作用。
  private func handleViewDisappeared() {
    // no-op
  }

  /// 用户点击列表项，派发跳转到详情页的命令。
  private func handleItemTapped(id: UUID) {
    guard let item = items.first(where: { $0.id == id }) else {
      return
    }
    dispatch(commands: [.pushDetail(item: item)])
  }

  /// 用户点击删除按钮，派发删除命令。
  private func handleDeleteButtonTapped(id: UUID) {
    dispatch(commands: [.deleteItem(id: id)])
  }

  /// 用户点击关闭按钮，派发关闭页面命令。
  private func handleCloseButtonTapped() {
    dispatch(commands: [.dismiss])
  }

  /// Manager 回流：列表加载完成，刷新 Item / Node 与加载态。
  private func applyItemsLoaded(_ loaded: [ProjectItem]) {
    items = loaded
    nodes = loaded.map { $0.toNode() }
    isLoading = false
  }

  /// Manager 回流：单条删除完成，从 Item / Node 中移除。
  private func applyItemDeleted(id: UUID) {
    items.removeAll { $0.id == id }
    nodes.removeAll { $0.id == id }
  }

  /// Manager 回流：加载失败，写入错误信息并退出加载态。
  private func applyLoadFailed(message: String) {
    errorMessage = message
    isLoading = false
  }

  /// 用户关闭错误提示，清空错误信息。
  private func applyErrorDismissed() {
    errorMessage = nil
  }

  // MARK: - Command 派发

  /// 统一派发 Command 批次；空数组不输出
  private func dispatch(commands: [ProjectCommand]) {
    guard !commands.isEmpty else { return }
    pendingReportedCommands.append(contentsOf: commands)
    commandContinuations.values.forEach { continuation in
      continuation.yield(commands)
    }
  }
}

extension ProjectStore {

  /// 项目 Store 的远端事件流稳定名称。
  nonisolated static let xloggerStoreName = "ProjectStore"
}
```

---

## Manager（只能由 Command 驱动，执行结果以业务数据返回，由 Controller 转 Event 投回 Store）

- Manager 的业务方法**只由 Controller 的编排函数（即每个 Command 对应的 private 方法）调用**，禁止被 View / Store 直接调用
- 业务方法以普通函数签名暴露：同步方法直接返回结果，异步方法用 `async`（必要时 `async throws`）；返回的是**业务数据**（Item / 业务值），不是 `[Event]`
- Controller 拿到返回值后，再通过 `store.handle(event:)` 投回 Store —— 形成「Controller 调 Manager → Manager 返回业务数据 → Controller 转 Event → Store」的单向边界
- `eventPublisher` 仅用于推送**与具体 Command 无关的主动事件**（如系统回调、长轮询、外部通知），由 Controller 的 `bindManagerEvents` 订阅
- Manager 内部对 Service 的调用同样走普通函数签名，不复用 Event/Command

```swift
final class ProjectManager {
  private let service: ProjectService
  private let eventSubject = PassthroughSubject<ProjectEvent, Never>()
  /// 主动事件流（非命令驱动）。
  var eventPublisher: AnyPublisher<ProjectEvent, Never> {
    eventSubject.eraseToAnyPublisher()
  }

  init(service: ProjectService = ProjectService()) {
    self.service = service
  }

  /// 拉取项目列表，由 Controller 的 fetchItems 编排函数调用。
  func fetchItems() async -> [ProjectItem] {
    do {
      let entities = try await service.fetchEntities()
      return entities.map { $0.toItem() }
    } catch {
      XLogger.error("fetchItems failed: \(error)")
      return []
    }
  }

  /// 删除指定项目，由 Controller 的 deleteItem 编排函数调用。
  func deleteItem(id: UUID) async {
    do {
      try await service.delete(id: id)
    } catch {
      XLogger.error("deleteItem failed: \(error)")
    }
  }
}
```

---

## Service（单一职责，处理数据存取）

```swift
actor ProjectService {
  func fetchEntities() async throws -> [ProjectEntity] { [] }
  func delete(id: UUID) async throws {}
  func save(_ entity: ProjectEntity) async throws {}
}
```

---

## View（只依赖 Store State 渲染，交互通过 Event 上报 Controller）

```swift
struct ProjectContentView: View {
  @ObservedObject var store: ProjectStore
  let onEvent: (ProjectEvent) -> Void

  var body: some View {
    Group {
      if store.isLoading {
        ProgressView()
      } else {
        List(store.nodes) { node in
          ProjectRowView(node: node)
            .swipeActions {
              Button("删除", role: .destructive) {
                onEvent(.deleteButtonTapped(id: node.id))
              }
            }
        }
      }
    }
    .alert(
      "错误",
      isPresented: Binding(
        get: { store.errorMessage != nil },
        set: { isPresented in
          if !isPresented { onEvent(.errorDismissed) }
        }
      )
    ) {
      Button("确定") { onEvent(.errorDismissed) }
    } message: {
      Text(store.errorMessage ?? "")
    }
  }
}

struct ProjectRowView: View {
  let node: ProjectNode

  var body: some View {
    VStack(alignment: .leading) {
      Text(node.title)
      Text(node.subtitle).foregroundStyle(.secondary)
    }
  }
}
```

---

## Model 三层

```swift
// Entity — 数据库层（默认优先 struct；SwiftData @Model 等框架要求引用类型时才使用 final class）
struct ProjectEntity {
  var id: UUID
  var title: String
  var createdAt: Date

  init(id: UUID = UUID(), title: String, createdAt: Date = .now) {
    self.id = id
    self.title = title
    self.createdAt = createdAt
  }

  func toItem() -> ProjectItem {
    ProjectItem(id: id, title: title, createdAt: createdAt)
  }
}

// Item — 业务层（struct，由 Store 统一持有）
struct ProjectItem {
  let id: UUID
  var title: String
  let createdAt: Date

  init(id: UUID, title: String, createdAt: Date) {
    self.id = id
    self.title = title
    self.createdAt = createdAt
  }

  func toNode() -> ProjectNode {
    ProjectNode(id: id, title: title, subtitle: createdAt.formatted())
  }
}

// Node — 视图层（struct，只含展示字段）
struct ProjectNode: Hashable, Identifiable {
  let id: UUID
  let title: String
  let subtitle: String
}
```
