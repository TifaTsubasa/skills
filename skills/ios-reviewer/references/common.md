# 通用审查指引与约束

本文件用于审查或重构 Photos 项目中跨层通用的代码问题，覆盖所有层级都可能触发的编码陷阱和写法约束，与 `architecture.md`、`service.md`、`manager.md` 的分层规则互补。

## 核心约束

- 禁止使用 `Dictionary(_:uniqueKeysWithValues:)` 由序列构造字典。当序列中存在重复 key 时，该方法会触发 fatalError 直接崩溃，属于运行时不可恢复的高风险写法；必须替换为 `reduce(into:)` 实现，遇到重复 key 时按“后者覆盖前者”或“保留前者”的明确策略合并。
- 每个 Swift 源文件最多只能声明一个顶层 `class`、`struct` 或 `enum`；同一文件内出现多个顶层类型时，必须拆分到独立文件。
- 对可在不同 App 复用的基础能力（通用工具函数、通用算法、通用数据结构封装等）或对基础类型（String/Array/Dictionary/Date/URL/Int 等）的能力拓展，必须先阅读 `Packages/Base/USAGE.md`，按其中的快速路由、能力地图和 AI 复用流程判断 `Packages/Base` 是否已有可复用能力；能复用则直接使用 Base 能力，不要在业务代码或 Photos 的各 Biz/Service/Util 里另起重复实现。如果确认没有，应在 `Packages/Base` 中新增（按其目录约定放到对应模块，如 Extensions / Utils / Managers 等），再由业务侧引用；不要把跨 App 可复用的基础能力沉淀到 Photos 业务包内部。
- 新增 private helper 也必须审查复用价值。凡是只做去重、过滤空值、分组、排序、映射、聚合、字典构建、日期/字符串/集合转换等通用同步处理的 helper，都不能因为是 private 就跳过；必须先用 `rg` 查当前模块、同层文件、`Packages/Base` 是否已有同语义实现。
- **通用集合处理复用检查**：审查新增 helper 或新增内联代码时，不以函数名作为触发条件，先抽取行为签名：输入/输出是什么集合或字典、是否保留顺序、用什么 key 判等、过滤了哪些无效值、是否有 I/O/事务/外部状态副作用。只要行为是纯同步集合变换，就必须先查 `Packages/Base/USAGE.md` 和同层已有实现；共享能力已能表达时必须输出 review case，要求复用稳定入口，而不是新增局部实现。

## 审查重点

- 搜到 `uniqueKeysWithValues` 时直接判为违规：检查入参序列是否存在重复 key 风险（来自模型数组、数据库结果、网络返回、map 转换结果等），只要 key 来源不是静态常量或编译期可证明唯一，即视为有重复崩溃风险。
- 看到由数组/map 结果构造字典的写法时，优先确认是否使用了 `uniqueKeysWithValues`；若用了其他写法（如 `reduce(into:)`、下标循环赋值），确认其重复 key 处理策略是否明确。
- 看到对基础类型（String/Array/Dictionary/Date/URL/Int 等）的能力拓展、通用工具函数、通用算法、通用数据结构封装时，检查其是否属于跨 App 可复用基础能力；若是，必须先阅读 `Packages/Base/USAGE.md` 判断是否已有可复用能力，再打开对应源码确认公开 API、actor 隔离和平台条件。
- 看到新增 helper 或新增函数内成段集合处理代码时，先看实现而不是名字：是否只读取入参/局部集合、构造 `Set`/`Dictionary`/`Array`、通过 `append` 或下标赋值汇总结果，且没有调用 Service/DAO/API/事务或写外部状态。符合这些特征时，按通用基础处理审查，并用行为签名搜索同语义实现。
- 对实现形态是保序去重的代码，无论函数名如何，只要通过 `Set`/字典记录已见元素并把首次出现元素写入结果，就必须把 `Packages/Base/USAGE.md` 中的集合能力路由和 `Packages/Base/Sources/Extensions/ArrayExtension.swift` 作为复用候选；可用 `rg -n "deduplicate\\(" ../Packages/Base Packages/Base` 辅助确认现有 API。
- 如果新增代码的主体是 `var seen = Set<...>()` 加循环/filter 保留首次出现元素，默认判定为 `deduplicate()` 或 `deduplicate(by:)` 可替代；只有同时包含业务特有副作用、事务 I/O 或无法由 key 闭包表达的规则时，才不按 Base 去重复用问题输出。

## 推荐重构方向

把 `Dictionary(seq, uniqueKeysWithValues:)` 替换为 `reduce(into:)`，并在闭包内显式表达重复 key 的合并策略。

```swift
// ❌ 禁止：序列存在重复 key 时会 fatalError 崩溃
let dict = Dictionary(items, uniquingKeysWith: \.value)
// 或
let dict = Dictionary(items.map { ($0.id, $0) }, uniqueKeysWithValues: { $0 })

// ✅ 推荐：reduce(into:) 实现，重复 key 时按"后者覆盖前者"合并
let dict = items.reduce(into: [String: Item]()) { result, item in
    result[item.id] = item
}

// ✅ 如需"保留前者"策略
let dict = items.reduce(into: [String: Item]()) { result, item in
    if result[item.id] == nil {
        result[item.id] = item
    }
}
```

基础能力复用：

- 先阅读 `Packages/Base/USAGE.md`，按“快速路由”和“能力地图”定位是否已有同语义能力；命中后再打开对应源码确认公开 API，能满足就直接引用 Base 能力并删除业务侧重复实现。
- 对保序去重，优先改为 `values.deduplicate()`、`items.deduplicate(by: \.id)` 或 `items.deduplicate { existing, item in ... }`；需要过滤空值时先 `filter` 再 `deduplicate`，不要新增只做“过滤空值 + Set 保序去重”的 helper。
- 未命中且确认属于跨 App 可复用基础能力时，按目录约定在 `Packages/Base` 新增（Extensions / Utils / Managers / Models 等），再由业务侧引用。
- 已沉淀在 Photos 业务包内、实际属于跨 App 基础能力的实现，迁移到 `Packages/Base` 并替换 Photos 内的调用点。
- 对只在当前业务域内复用的基础处理，优先收敛到已有同层 helper 或明确命名的域内 Util；不要在同一 Service、同一目录或相邻业务文件里复制多份 private 去重/过滤函数。

## Review 结论写法

- 对使用 `uniqueKeysWithValues` 的代码，说明“使用了 `Dictionary(uniqueKeysWithValues:)`，序列存在重复 key 时会触发 fatalError 崩溃，属于运行时高风险写法”，指出 key 来源和重复风险，并建议替换为 `reduce(into:)`，同时明确重复 key 的合并策略（后者覆盖前者或保留前者）。
- 对基础类型拓展或通用工具函数等跨 App 可复用能力，说明“该能力属于可在不同 App 复用的基础能力，沉淀在业务包内部会形成重复实现”，指出 `Packages/Base/USAGE.md` 中是否已有可复用能力（或确认未命中），并建议直接复用、在 `Packages/Base` 新增或把现有实现迁移到 `Packages/Base`。
- 对重复 private helper，说明“新增 helper 只是基础同步处理，且当前模块或 `Packages/Base` 已有同语义实现”，列出新增位置和已有实现位置，并建议复用或收敛到一个稳定入口。
- 对未复用 Base 去重能力，说明“新增 helper 手写了保序去重逻辑，但 `Packages/Base/USAGE.md` 已路由到 `ArrayExtension.swift` 的 `deduplicate`”，指出应使用的重载，例如 `assetIds.filter { !$0.isEmpty }.deduplicate()` 或 `assets.filter { !$0.assetId.isEmpty }.deduplicate(by: \.assetId)`。
