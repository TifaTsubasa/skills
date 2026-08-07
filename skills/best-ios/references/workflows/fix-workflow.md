# Fix 流程

当用户描述 iOS bug 且希望用「先以 Store 单测复现、再修复」的 TDD 流程修问题时，按本流程执行：围绕相关 Store 搭建 mock 环境 → 写出一个能**先失败**的 Store 单测（复现 bug）→ 修代码直到这个单测通过。

不写 ad-hoc 脚本、不在 Manager/Service 层猜，所有验证都落回到 Store 单测。

## 适用范围

- Bug 可以落回到核心 SPM 包下某一个 Store（`Packages/<XxxCore>/Sources/<XxxCore>/Store/`）的 Event→Command / Event→State 行为
- 若用户描述的问题明显属于 View / Controller / Manager / Service 范畴，先跟用户确认是否真的需要走本流程；Store 无法单独复现时应说明原因，不要硬套

## 前置阅读

开始前必读以下内容，用于确认分层与数据流规则：

- `../core/architecture.md` — Store 的职责、单测范围、Event/Command 边界
- `../core/swift-templates.md` — Event → Command 调度与 `handle(event:)` / `commands: AsyncStream<[Command]>` / `@Published` 状态字段的强制模板

## 执行流程

按顺序执行三步，每一步完成后再进入下一步；缺任何一步都视为未完成。

### 1. 理解 bug 并与用户确认

- 先仔细阅读用户描述，结合仓库上下文思考：触发场景是什么？预期行为是什么？当前观察到的异常现象是什么？
- 如果描述有歧义、缺少关键信息（触发路径、涉及的功能模块、复现步骤、期望结果），先整理出疑问点
- 用一段简短的复述 + 关键疑问点跟用户确认理解是否正确；**必须等到用户确认后再进入下一步**，不要凭猜测直接开始定位代码
- 若用户澄清后发现问题不适合走本流程（非 Store 层可复现），在此步提前结束并说明原因

### 2. 定位代码中问题的位置

- 在用户确认理解后，根据问题场景定位承担该业务的 Store 源文件（优先看 `Packages/<XxxCore>/Sources/<XxxCore>/Store/` 的文件名与 Event 枚举）
- 通读相关 Store：锁定触发路径上的 Event、涉及的内部状态字段、会产出的 Command，并标出最可能出问题的代码片段
- 找到对应测试文件（`Packages/<XxxCore>/Tests/<XxxCore>Tests/Store/<StoreName>Test.swift`），了解既有测试覆盖
- 向用户简要说明定位结果：涉及哪个 Store、哪些 Event / 字段、怀疑的代码位置，方便用户及时纠偏
- 若排查后发现根因在 Manager / Service / View，停下来与用户确认是否仍按本流程继续，不要硬套 Store 单测

### 3. 按 TDD 流程修复 bug

按顺序完成下面三小步，任何一步缺失都视为未完成。

#### 3.1 搭建 mock 环境

- 基于步骤 2 定位到的 Store 和测试文件，构造最小可复现的测试输入
- 复用现有 `MockHelper` / 已有工厂方法来构造 Item、Node、快照等输入；只有在现有辅助不够时才在测试文件内就近补一个 `makeXxx` 函数，禁止新建 Mock Service / Mock Manager（Store 不依赖它们）
- mock 环境以「最小可复现」为目标：用最少的资产 / 快照 / 模式切换还原用户描述的场景

#### 3.2 写一个先失败的单测复现 bug

- 在对应 `*StoreTest.swift` 中新增 `@Test("……")` 方法，方法名用 `snake_case` 概括场景，标题用中文短句描述期望
- 测试体：
  1. 构造 3.1 得到的 mock 环境
  2. 按用户描述的触发顺序 `store.send(.xxx)`；需要观察命令时，用测试内的异步 recorder 订阅 `store.commands`，并通过 `waitForBatchCount(_:)` / `waitForIdle()` 等条件等待 helper 确认异步流消费完成
  3. 用 `#expect` / `Issue.record` 断言「正确行为」，让断言在当前 buggy 代码下失败
- 运行核心包测试确认该单测**确实失败**，且失败信息与 bug 现象一致；若编译报错，先修好编译错误让它能跑到断言，再确认断言失败
- 此时不要动业务代码；如果单测在 buggy 代码下意外通过，说明复现不准确，回到 3.1 调整 mock

运行核心包单元测试的命令（按所在项目实际的 project / scheme / testPlan / 模拟器机型替换占位符；若项目提供了专用测试技能或脚本，优先用它）：
```bash
xcodebuild test -project <项目>.xcodeproj -scheme <XxxCore>Tests -testPlan <XxxCore>Tests -destination 'platform=iOS Simulator,name=<模拟器机型>'
```

#### 3.3 修复 bug 让单测通过

- 只改必要的 Store / Model / Util 代码；不要顺手做重构或引入新抽象
- 保持 Store 分层约束（不得依赖 Manager / Service；Event 遵循 `EventType`，Command 遵循 `CommandType`，二者仍是带 payload 的 enum）
- 修复后的代码结构与调度方式必须回归到 `../core/swift-templates.md` 的模板写法；不能为了让测试通过继续保留与模板冲突的实现
- 再次运行核心包测试，确认：
  - 新增单测通过
  - 既有单测全部保持通过（不允许被「改断言」的方式掩盖回归）
- 若修复过程中发现 bug 真正根因在 Manager/Service/View，停下来向用户说明，并询问是否扩大修复范围

## 产出

向用户汇报：

1. 所涉及的 Store 与触发事件序列（简述复现路径）
2. 新增测试文件 / 测试方法的位置与名称
3. 修复前后的失败 → 通过对比（引用测试名即可，不需要粘贴大段日志）
4. 修改到的源文件列表，以及是否影响其他测试

## 注意

- 测试框架使用 Swift Testing（`import Testing`），用 `@Test` / `#expect`；不要改成 XCTest
- Store 单测不要 mock 时间、通知等系统副作用；如果 bug 依赖这些，先与用户确认是否该在 Store 层复现
- 禁止 `try?`；若测试内需要 throwing 调用，用 `try` 或 `do/catch` 并在 catch 里 `Issue.record`
- 遵循仓库 2 空格缩进、一个文件一个类的约定
