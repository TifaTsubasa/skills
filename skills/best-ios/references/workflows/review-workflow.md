# Review 流程

当用户要求「审查 / 检查 / review / 评估 / 找问题」时，只产出问题清单与建议，不直接改代码。

## 执行步骤

1. **界定审查范围**
   - 明确用户要审查的目录、文件或 PR 改动集
   - 读取 `../core/architecture.md`，以作为对照基准

2. **逐层核查约束**
   - 文件分层与目录结构：被审查页面是否在业务目录下独立成 `<PageName>/` 目录并按 `Entry/ Controllers/ Managers/ Services/ Views/` 拆分；Store / Event / Command / Model / Util 是否放进核心 SPM 包（`Packages/<XxxCore>/`）的 `Store/ Model/ Utils/` 子目录，而非散落在主工程；对应单测是否在包内 `Tests/`
   - 架构层级：Page/Controller/Manager/Store/Service/View/Model/Util 的职责与依赖约束
   - 依赖关系：各层之间的依赖方向是否符合架构要求（Page/ViewController → Controller → Manager/Store；View 仅依赖 Item/Node 与回调；Manager/Service 不得反向依赖 Controller/Page；Store 不得依赖 UIKit/SwiftUI 与跳转栈），是否存在跨层直接引用、循环依赖或越级调用
   - 渲染职责：是否存在专门的 `ContentView`（SwiftUI）或等价的纯渲染视图组件承担页面渲染；入口 `Page` / `ViewController` 是否仅负责装配（持有 Controller、注入跳转回调、桥接 NavigationPath / sheet binding），而**不**直接编写大量渲染代码或业务 UI 逻辑；渲染所需数据是否通过 Item/Node + Binding/回调注入到 ContentView，而非由入口层自行拼装
   - 模型分层：Entity / Item / Node 的使用场景与转换路径是否正确；Item 是否由 Store 统一持有
   - 模型必要性：本次改动是否新增了模型（Entity / Item / Node 或其它结构体）？每个新增模型是否真有必要——能否复用已有模型，或在已有模型上扩展字段 / 计算属性来承载，而不是新造一个；是否存在与既有模型职责重叠、字段高度相似的冗余模型
   - 数据流：Event / Command 是否为带 payload 的 enum，并分别遵循 `EventType` / `CommandType`；是否单向流动；Event→Command 的调度是否收敛在 Store 内部；**Command 是否只用于驱动 Manager 业务方法或驱动页面跳转**（Store 自身状态更新应在 `handle(event:)` 处理函数内直接完成，不经 Command）；Store 命令出口是否是 `commands: AsyncStream<[Command]>`，是否仍残留 `commandPublisher` / `PassthroughSubject<[Command], Never>`；Store 是否通过 `XLoggerStoreReporter<Event, Command>` 在 `handle(event:)` 末尾一次性上报 event + 同批 commands，`dispatch(commands:)` 是否累积到 `pendingReportedCommands`，是否暴露 `nonisolated static let xloggerStoreName`，有无历史旁路 `dispatch` 缺隔离标记
   - Controller ↔ Manager 边界：Manager 业务方法是否以普通函数签名暴露并返回**业务数据**（不是 `[Event]`）；是否只由 Controller 的编排函数调用；Controller 是否持有 `commandTask` 用 `for await` 消费 Store 命令流并在 `deinit` 取消；Controller `route(_:) async` 是否只做 switch + 调用 private 编排函数（覆盖业务类与跳转类 Command）；业务类编排函数是否直接调用 Manager 后把返回值转 Event 投回 Store，且没有在函数内部再创建二次 `Task`
   - Controller ↔ Page / ViewController 边界：跳转类 Command 是否在编排函数内调用 `init` 注入的跳转回调（`onPushDetail` / `onPresentSheet` / `onDismiss` 等）；Controller 自身是否完全没有持有 / 操作 `UIViewController` / `UINavigationController`；Page / ViewController 是否在初始化 Controller 时显式注入了所有跳转回调，并仅在回调闭包内执行 push / present / dismiss / pop；跳转状态（`UINavigationController` / `NavigationPath` / sheet binding）是否完全由 Page / ViewController 自己持有，没有泄漏到 Store
   - 模板一致性：实际代码结构、命名、交互方式是否与 `../core/swift-templates.md` 一致；凡是不一致之处，都要视为明确审查项，而不是"风格差异"
   - Util 抽取：Manager / Service 内是否还残留大段纯同步的数据加工 / 转换 / 过滤 / 聚合 / 计算 / 规则判定逻辑没有抽到 Util？已抽出的 Util 是否是纯函数式接口（无副作用、无状态）、是否只依赖系统库 / Model / Util、是否放在核心 SPM 包内并补了单测
   - 测试范围：Store / Util / Node / Item 的逻辑是否被单元测试覆盖

3. **按 P0 / P1 / P2 划分优先级**
   每个问题必须先归入下列三档之一，再写进报告：

   - **P0（必须修复 / 阻塞）**：违反架构硬约束、导致数据流断裂、引发并发不安全 / 内存泄漏 / 崩溃风险、跨层直接引用或循环依赖、Store 触达 UIKit / 跳转栈、Command 被滥用为状态更新、Manager 反向依赖 Controller 等核心规则违背。这类问题不修复就不能合入。
   - **P1（重要 / 应尽快修复）**：模板结构偏离明显但暂未引发故障（命名 / 目录拆分错位、Controller 未用 `commandTask` 消费命令流、缺少 `xloggerStoreName`、Util 该抽未抽、单测覆盖缺口、模型职责重叠等）。不阻塞当前合入，但需要在后续迭代中收敛。
   - **P2（建议 / 可优化）**：风格一致性、命名清晰度、注释、可复用性、轻微冗余等改进建议。可选修复。

4. **记录问题清单**
   对每个问题按以下统一结构记录（**问题说明** 与 **改进思路** 缺一不可）：

   ```
   ### [P0 / P1 / P2] <一句话概括问题>
   - **位置**：`文件:行号`（多处时按 `文件A:行号`、`文件B:行号` 列出）
   - **违反的约束**：引用 `../core/architecture.md` 或 `../core/swift-templates.md` 中的具体规则条目
   - **问题说明**：用 2-4 句话讲清楚现状是什么、为什么违反约束、可能带来什么影响（数据流断裂 / 并发风险 / 测试缺口 / 维护成本等）。不要只说"不符合规范"，要落到具体表现。
   - **改进思路**：给出可执行的修正方向（应该怎么改、参考哪个模板段落、是否需要补单测 / 抽 Util / 调整依赖方向）。若改动较大，可拆成 2-3 步骤。不要写完整代码，但要让读者拿到思路就能落地。
   ```

5. **输出审查报告**
   报告必须按下面的顺序组织：

   1. **总体结论**：是否符合架构规范、整体健康度、主要风险点（3-5 句话）。
   2. **P0 问题清单**：逐条列出，按上面的结构展开；若无 P0 则明确写「无 P0 问题」。
   3. **P1 问题清单**：同上。
   4. **P2 问题清单**：同上。
   5. **统计摘要**：P0 / P1 / P2 各多少条，集中在哪些层（Store / Controller / Manager / View 等），便于后续认领。

   - 不直接修改代码，除非用户明确要求进入 Refactor 模式
   - 即使整体符合规范，也要明确写出"未发现 P0 / P1 问题"，避免读者误以为漏审

## 改进思路参考项

写「改进思路」时优先复用以下标准建议，命中即按对应措辞表述。

1. **Controller 直接持有 Service** → 将 Service 下沉为 Manager 的依赖，Controller 改为只依赖 Manager。
