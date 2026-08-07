# Manager 审查指引与约束

本文件用于审查或重构 Photos 项目中的 Manager，尤其是涉及 Manager 函数职责、Service 数据获取、ManagerUtil 数据整合或 Manager 内复杂数据处理时。

## 核心约束

- Manager 的编排函数分两类处理：有上游依赖时顺序编排，无上游依赖时并发获取。
- 当不同 Service 的获取存在上游数据要求时，Manager 按“Service 获取数据 -> ManagerUtil 整合数据 -> ServiceB 基于上游数据继续获取 -> ManagerUtil 整合数据 -> 返回数据”的方式编排。
- 当编排函数能够一次性从不同 Service 获取数据，且这些数据之间没有上游依赖时，Manager 应并发获取后直接返回给 Store 处理，不需要引入 ManagerUtil。
- Manager 函数内严禁出现复杂的数据整合逻辑；需要复杂整合时必须下沉到 ManagerUtil，不需要整合时不要强行引入 ManagerUtil。
- Manager 不直接产出底层数据，底层数据必须由 Service 提供。
- Manager 可以承接简单的服务调用前后处理，例如轻量参数组装、单个返回值判断、简单默认值补齐或一次性调用结果选择；这些处理必须服务于编排，不应沉淀成可复用底层能力。
- 当服务处理变复杂、需要跨 Manager 复用、包含底层 I/O 封装、缓存/重试/分页/权限/资源读取等服务策略时，必须下沉到 Service；如果复杂点是纯同步数据整合，则下沉到 ManagerUtil。
- Manager 可以按业务流程串联多个 Service 与 ManagerUtil，但每一步都应清晰表现为“Service 获取数据”、“ManagerUtil 整合数据”或“并发获取后返回 Store”。

## 推荐函数结构：有上游依赖

```swift
// 按上游依赖串联 Service 数据并完成整合编排
func get() {
    // 从 service 获取上游数据
    // ManagerUtil 整合上游数据
    // 使用上游数据从 serviceB 获取数据
    // ManagerUtil 整合最终数据
    // 返回整合结果
}
```

## 推荐函数结构：无上游依赖

```swift
// 并发获取无依赖的 Service 数据
func get() async {
    // 并发从 service 获取数据
    // 并发从 serviceB 获取数据
    // 直接返回给 Store 处理
}
```

## 审查重点

- 先判断编排函数中的不同 Service 调用是否存在上游数据依赖；有依赖才按顺序编排并使用 ManagerUtil 整合。
- 看到多个互不依赖的 Service 调用时，检查是否可以一次性并发获取，并直接把结果返回给 Store。
- 看到 Manager 函数中出现多层循环、复杂分组、排序、去重、映射、聚合、状态合并或跨模型转换时，检查这些逻辑是否应该移到 ManagerUtil。
- 看到 Manager 函数直接拼装复杂返回模型时，检查数据是否应由 Service 提供、整合是否应由 ManagerUtil 完成。
- 看到 Manager 函数中只有轻量参数组装、单个返回值判断、简单默认值补齐或一次性调用结果选择时，不要直接判为违规；继续检查它是否仍服务于编排。
- 看到 Manager 函数内的服务处理包含可复用底层能力、底层 I/O 封装、缓存/重试/分页/权限/资源读取等服务策略时，要求下沉到 Service。
- 看到 Manager 函数里混杂 Service 调用和大段处理逻辑时，要求按依赖关系拆成清晰的 Service 获取步骤、ManagerUtil 整合步骤或并发获取后返回 Store 的步骤。

## Review 结论写法

- 对 Manager 内复杂整合逻辑，说明“Manager 编排函数承担了复杂数据整合，违反 Manager 不在函数内做复杂整合的规则”，并建议把整合逻辑下沉到 ManagerUtil。
- 对 Manager 内复杂服务处理，说明“Manager 承担了复杂服务处理，超过简单服务调用前后处理范围”，并建议把可复用底层能力或服务策略下沉到 Service。
- 对没有上游依赖的多个 Service 调用，说明“这些 Service 数据可一次性并发获取，不需要引入 ManagerUtil”，并建议并发获取后直接返回给 Store 处理。
- 对 Manager 直接产出底层数据，说明数据来源应该由 Service 提供，并建议补齐或调整对应 Service 能力。
