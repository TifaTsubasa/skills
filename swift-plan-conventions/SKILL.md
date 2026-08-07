---
name: swift-plan-conventions
description: Swift 编码方案的 plan 模式守门人——只在 plan / 编码方案 / 实现思路阶段触发，对 .swift 文件清单与 class / struct / enum / protocol 命名做强约束。当 plan 中出现「新建 / 拆分 / 合并 .swift 文件」「新增 / 重命名类型或协议」「Delegate / DataSource / 能力接口 / 代理 / 回调」这类词，或方案里出现具体类型 / 协议命名提案（含 `Xxx`、`IXxx`、`XxxProtocol` 等任意命名风格）时必须主动使用本 skill。强制两条硬规则：①每个 .swift 文件只允许一个顶层 class / struct / enum（同文件 extension、嵌套类型、private helper 放行）②协议命名遵循 Swift API Design Guidelines（能力类 `-able` / `-ible`，行为或角色用名词或 `-ing`，Delegate / DataSource 沿用 UIKit「宿主类型 + Delegate / DataSource」风格）。触发后必须直接把 plan 的文件清单、类型与协议名改写成合规最终版，不要只列规则等落地阶段对照。本 skill 不负责其他 Swift 风格规则（缩进、可选解包、并发等）——那些由 best-ios 等 skill 负责。
---

# Swift Plan 编码规范守门人

本 skill 只在**写 plan / 设计编码方案**的阶段生效，作用是把方案在被采纳之前调整成符合下面两条规范的最终版。代码落地阶段更广的规则（缩进、并发、可选解包、架构分层等）由 `best-ios` skill 负责，本 skill 不重复。

## 工作方式

在 plan 模式下，每当方案涉及以下任一项，启用本 skill：

- 新建 / 修改 / 拆分 / 合并 `.swift` 文件
- 新增或重命名 `class` / `struct` / `enum` / `protocol`
- 设计协议接口（能力类 / Delegate / DataSource / 角色描述等）

你需要**直接把 plan 的「文件清单」和「类型 / 协议命名」部分改写成最终合规形态**：

- 文件清单：每个新建文件点名它装的那一个顶层类型；超过 1 个的拆开
- 类型 / 协议名：在 plan 里就给出最终名字，标注它落到哪一类规则

不要先输出一份不合规 plan、再附上一段「请按规范修正」。规范是 plan 的硬约束，不是 plan 的事后备注。

---

## 规则一：一个文件一个顶层类型

只针对**顶层** `class` / `struct` / `enum`。下面的边界一定要分清，否则会误伤合理写法、也容易漏掉真正的违规。

### 算违规

❌ 同一 `.swift` 文件出现 **多个顶层** `class` / `struct` / `enum`：

```swift
// PhotoModels.swift  ← 违规
struct PhotoEntity { ... }
struct AlbumEntity { ... }
enum PhotoSortOrder { ... }
```

修正：每个顶层类型独立成文件——

- `PhotoEntity.swift`
- `AlbumEntity.swift`
- `PhotoSortOrder.swift`

### 不算违规（放行）

✅ 主类型 + 同文件 `extension`：

```swift
// PhotoListController.swift
final class PhotoListController { ... }

extension PhotoListController: UITableViewDataSource { ... }
extension PhotoListController: UITableViewDelegate { ... }
```

✅ 主类型 + 嵌套类型（命名空间手段，不属于「顶层」）：

```swift
// PhotoStore.swift
final class PhotoStore {
  enum State { case idle, loading, loaded }
  struct Snapshot { ... }
}
```

✅ 主类型 + 同文件 `private` / `fileprivate` helper：

```swift
// AssetGroupingUtil.swift
enum AssetGroupingUtil { ... }

private struct GroupingBucket { ... }
```

> Why：本规则的目的是让「按类型名找文件」一一对应，避免主工程里出现 `PhotoModels.swift` 这种装载多个领域类型的杂烩文件。嵌套类型作为命名空间是 Swift 推荐手法，不破坏「按类型找文件」的可发现性；同文件 extension / private helper 只服务于主类型自身，也不破坏映射关系，因此都放行。

### 在 plan 里怎么落

plan 列文件清单时，**每个新建 / 拆分的文件都要点名它装的那一个顶层类型**。

❌ 不合规的 plan 片段：

> 新建 `PhotoModels.swift`，包含 `PhotoEntity`、`AlbumEntity`、`PhotoSortOrder`

✅ 合规的 plan 片段：

> 新建以下文件，每个仅一个顶层类型：
> - `PhotoEntity.swift` — `struct PhotoEntity: Codable`
> - `AlbumEntity.swift` — `struct AlbumEntity: Codable`
> - `PhotoSortOrder.swift` — `enum PhotoSortOrder`

如果用户原始诉求里出现了「在一个文件里定义几个模型」这种暗示违规的表述，**不要静默接受**——在 plan 里直接拆开并简短说明：「按规范拆为 N 个文件，每个文件一个顶层类型」。

---

## 规则二：协议命名按 Swift 官方风格

Swift API Design Guidelines 给协议命名分了清晰的三类。plan 里出现 `protocol` 时，先判断它属于 A / B / C 哪一类，再用对应形式落名。

### 类型 A：能力类协议（"能做什么 / 具备某种性质"）

**形式：以 `-able` / `-ible` 结尾的形容词**。

标准库示范：`Equatable`、`Comparable`、`Hashable`、`Identifiable`、`Codable`、`Sendable`、`Decodable`。

项目命名示例：

- 表示「可被某种维度分组」的协议 → `Groupable`
- 表示「可被排序」的协议 → `Sortable`
- 表示「能被快照成字符串描述」 → 倾向 `CustomStringConvertible`（系统已有）

❌ 反例：`PhotoGroupingProtocol`、`IGroupable`、`GroupableProtocol`、`HasGrouping`
✅ 正例：`Groupable`

### 类型 B：描述行为 / 角色的协议（"是什么 / 在扮演什么角色"）

**形式：名词，或以 `-ing` 结尾的现在分词**。

标准库示范：`Collection`、`Sequence`、`Iterator`、`ProgressReporting`、`CustomStringConvertible`。

项目命名示例：

- 描述「时间线资源来源」的角色 → `TimelineAssetSource`
- 描述「正在执行整理流程」的角色 → `AssetArranging`
- 描述「日志报告者」的角色 → `LogReporting`

❌ 反例：`ITimelineAssetSource`、`TimelineAssetSourceProtocol`、`HasTimelineAssetSource`
✅ 正例：`TimelineAssetSource`、`AssetArranging`

### 类型 C：Delegate / DataSource（UIKit / AppKit 风格回调）

**形式**：以**宿主类型名**为前缀，加 `Delegate` / `DataSource` 后缀。

UIKit 示范：`UITableViewDelegate`、`UITableViewDataSource`、`UICollectionViewDelegateFlowLayout`。

项目命名示例：

- `TimelineArrangeController` 的回调代理 → `TimelineArrangeControllerDelegate`
- `RandomAssetPicker` 提供资源数据的接口 → `RandomAssetPickerDataSource`

❌ 反例：`TimelineDelegate`（前缀不明确，看不出宿主是谁）、`TimelineArrangeControllerDelegateProtocol`（多余 `Protocol` 后缀）、`DelegateOfTimelineArrangeController`（语序错位）
✅ 正例：`TimelineArrangeControllerDelegate`、`RandomAssetPickerDataSource`

### 跨类禁忌（A / B / C 都不允许）

无论协议属于上面哪一类，下面的写法一律禁止：

- **Java / C# 风格前缀**：`I` / `P` 开头 — ❌ `IPhotoSource`、`PPhotoSource`
- **多余的 `Protocol` 后缀**：协议名本身已经在 `protocol` 关键字后定义，再加 `Protocol` 后缀是冗余 — ❌ `PhotoSourceProtocol`、`GroupableProtocol`
- **`Has...` / `Does...` 等动宾开头**：表达"具备能力"应当用 `-able` 形容词收尾，而不是动词开头 — ❌ `HasIdentifier`、`DoesGrouping`

> Why：这三种禁忌都是从其他语言迁移过来的命名习惯。Swift 协议名应当读起来像「形容一个类型是什么 / 能做什么 / 扮演什么角色」，三种禁忌写法破坏了这种语义可读性，并且在 Swift 社区中也是公认的反模式。

### 在 plan 里怎么落

plan 提到新增 / 重命名协议时，**直接给出最终协议名 + 标注它落到 A / B / C 哪一类**，不要把命名留给落地阶段再纠结。

❌ 不合规的 plan 片段：

> 新增一个协议用于资源整理回调，命名待定，暂叫 `TimelineProtocol`。

✅ 合规的 plan 片段：

> 新增协议 `TimelineArrangeControllerDelegate`（类型 C：Delegate 回调），方法包含 `…didFinishArranging:`、`…didCancelArranging:`，宿主为 `TimelineArrangeController`。

如果原 plan 已经给出了一个不合规的名字（比如 `IPhotoSource`、`PhotoSourceProtocol`），**不要保留并加注释**，直接替换为合规名，并简短标注「按规范从 `XXX` 改为 `YYY`（理由：禁用 `I` 前缀 / 多余 `Protocol` 后缀 / ...）」。

---

## 触发判断

进入 plan 模式后，扫一遍方案文本，命中任意一项就启用本 skill：

| 命中信号                                                           | 启用动作                          |
|----------------------------------------------------------------|-------------------------------|
| plan 出现「新建 / 拆 / 合并 / 重命名 .swift 文件」「文件清单」「目录结构」               | 用规则一审查并改写文件清单                 |
| plan 中 `class` / `struct` / `enum` 数量 ≥ 2 且未明确拆到不同文件             | 用规则一拆分到独立文件                   |
| plan 出现 `protocol` 字样、或「代理」「回调」「能力接口」「DataSource」「Delegate」 | 用规则二给出最终协议名 + 标注 A / B / C 分类 |
| plan 出现具体命名提案（任何 `Xxx` / `IXxx` / `XxxProtocol` 等候选名）          | 立即按规范替换为最终名                   |

**没命中任何信号 → 不要主动展开规范**，避免在纯算法实现、Bug 修复、UI 微调等不涉及类型 / 协议增删的场景里制造噪声。

## 与其他 skill 的边界

- 涉及 Page / Controller / Manager / Store / Service / View / Model 的**架构层级与数据流**设计 → 仍由 `best-ios` skill 主导，本 skill 只在它产出 plan 的「文件清单 / 协议命名」部分补刀
- 已经在**写代码**而不是写 plan → 本 skill 不触发；规范的兜底归落地阶段的 review 或 `best-ios`
- 翻译文案 / 日志读取 / BDD 拆需求 等其他垂直 skill 与本 skill 完全不相关

## 输出 plan 前自检

把 plan 输出给用户之前，逐项自问一遍：

- [ ] plan 列出的每个 `.swift` 文件，是不是只放了一个顶层 `class` / `struct` / `enum`？（嵌套类型 / extension / private helper 不算）
- [ ] plan 中出现的每个 protocol 名字，是不是落在 A / B / C 三类中的一类，并避开了 `I` 前缀、多余 `Protocol` 后缀、`Has...` / `Does...` 开头？
- [ ] 如果命中触发信号但 plan 里没有显式的文件清单 / 协议命名，是不是已经把它们补上？

任一条没过 → 把 plan 改了再输出，不要留给后续阶段。
