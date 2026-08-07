# Service 编译/重构指引与约束

本文件用于审查或重构 Photos 项目中的 Service，尤其是涉及 PhotoKit/Photos.framework、XPhotoKit 能力边界、Service 编译失败或 Service 分层违规时。

## 核心约束

- Service 是单一领域能力的封装，负责稳定、可复用、方向明确的底层能力。
- **Service 类型必须声明为 `class`**（`final class XxxService`），不允许用 `struct` / `enum` / `actor` 承载；由 Manager 通过依赖注入持有，保持引用语义与单一实例。
- **Service 不需要遵守 `Sendable`。** 不要因为 Service 未标注 `Sendable` / `@unchecked Sendable` 就输出 review case，也不要为了满足 `Sendable` 建议把 Service 改成 `actor` 或 `struct`；并发安全由调用侧（Manager 的调度与隔离）保证。如果确实存在跨隔离域共享同一 Service 实例的实际风险，放到 `Open Questions` 里请用户确认，不判为违规。
- Service 的功能必须领域单一，专注一个方向，例如数据库、网络请求、文件系统、PhotoKit 访问、缓存或日志。
- 一个 Service 不能同时承担多个方向的职责，例如既做数据库写入又做网络请求编排，或既做 PhotoKit 查询又做业务状态聚合。
- Service 不能依赖其他 Service，包括持有、初始化、静态单例调用、构造参数注入或在方法内部临时创建。
- Service 可以依赖系统框架、底层客户端、DAO、Repository、纯工具函数或 value type，但不能把另一个 Service 当作协作者。
- Manager 负责组合多个 Service；如果一个 Service 需要另一个 Service 才能完成任务，优先把编排上移到 Manager。
- **Service 函数铁律**：Service 函数只接收外部已处理好的调用数据，并直接执行底层服务/API 调用；尽可能避免在 Service 内做数据过滤、分组、排序、映射、聚合、规则判断或业务状态整合。
- 从 Photos 系统库调用照片能力时，统一使用 XPhotoKit 提供的 Service 能力。
- 如果 XPhotoKit 缺少需要的照片能力，先在 XPhotoKit 中补齐对应 Service 能力，再让业务侧调用 XPhotoKit。
- 不要在业务 Service 中绕过 XPhotoKit 直接沉淀 PhotoKit 原始遍历、资源读取、授权、缩略图/图片请求、asset 查询等照片底层能力。
- Service 中不要沉淀重复能力，语义相近、仅入参或条件略有差异的能力应复用同一个函数（通过参数化、可选参数、集合入参或枚举区分），避免出现多个函数分别做同源的底层调用，造成能力分散、行为不一致和重复维护。
- Service 重复能力不只看 public/internal 函数，也包括 private helper。新增 helper 如果只是做过滤空 id、按 id 保序去重、分组、排序、映射、聚合、字典构建等基础同步处理，必须和同一 Service、同一 Biz 目录、相关 Entity/DAO 文件里的已有 helper 对照，不能用 private 作用域掩盖重复实现。

## 审查重点

- 看到 `struct XxxService`、`enum XxxService`、`actor XxxService` 时直接判为违规，要求改成 `final class XxxService`。
- 看到 Service 上标注 `Sendable` / `@unchecked Sendable`，或看到 Service 未标注 `Sendable` 时，都不作为问题输出；本项目不对 Service 提 `Sendable` 要求。
- 看到 `PHAsset`、`PHFetchResult`、`PHPhotoLibrary`、`PHImageManager`、`PHAssetResource`、`Photos`、`PhotoKit` 等调用时，先判断是否应该落到 XPhotoKit。
- 看到 `DatabaseService.shared`、`ImageHashService()`、`SomeService.shared`、`let xxxService`、`var xxxService` 等出现在 Service 内时，检查是否构成 Service 依赖 Service。
- 看到 Service 同时处理照片查询、数据库写入、缓存编排、业务聚合状态时，检查是否应拆分底层能力并把业务编排移到 Manager。
- 看到 Service 函数内部出现过滤、分组、排序、映射、聚合、规则判断、跨模型转换或业务状态整合时，检查这些数据是否应在外部先处理好，再把调用所需数据传给 Service。
- 看到多个 Service 函数名相近、入参或条件略有差异、但底层调用同一个系统框架/客户端/DAO/Repository 时，检查是否构成重复能力，能否通过参数化、可选参数、集合入参或枚举合并成同一个函数。
- 看到新增 Service helper 名称包含 `unique`、`deduplicate`、`normalize`、`group`、`map`、`filter`、`sort`、`merge`、`build` 时，必须用 `rg` 搜同层和相关数据库扩展文件；如果已有同语义 helper，应判为 Service 内重复小能力。
- 如果补 XPhotoKit 能力会导致上层编译失败，优先修正 XPhotoKit 的公开 API、访问级别、模型导出和调用点类型，而不是在业务层复制 PhotoKit 逻辑。

## 推荐重构方向

- Service 依赖 Service：移除 Service 间依赖，把两个 Service 注入到 Manager，由 Manager 串联调用并维护业务语义。
- Service 内处理调用前数据：把过滤、分组、排序、映射、聚合、规则判断或业务状态整合移到外部合适层级，让 Service 只接收已处理好的调用数据并执行服务/API 调用。
- Service 重复能力：把语义相近、底层调用同源的多个函数合并为一个，通过参数化、可选参数、集合入参或枚举区分差异点，保留一个稳定入口，删除冗余函数；调用点统一改到合并后的函数。
- Service 重复 private helper：优先复用已有 helper；如果确实需要事务内同步调用，抽出一个可在事务上下文复用的静态 helper 或域内 Util，不要复制一份近似实现。
- 业务 Service 直接调用 PhotoKit：把底层照片能力补到 XPhotoKit Service，业务侧改为调用 XPhotoKit。
- XPhotoKit API 不足：在 XPhotoKit 新增最小必要接口，保持参数和返回值贴近业务需要，避免暴露不必要的 PhotoKit 细节。
- 编译错误来自访问级别：优先确认类型、方法、初始化器和模型属性是否需要对业务模块公开。
- 编译错误来自类型不匹配：优先在 XPhotoKit 边界做适配，避免业务层散落桥接逻辑。

## 典型证据搜索

```bash
rg "class .*Service|struct .*Service|actor .*Service|protocol .*Service" .
rg "let .*Service|var .*Service|: .*Service|= .*Service\\(" .
rg "import Photos|import PhotoKit|PHAsset|PHFetchResult|PHPhotoLibrary|PHImageManager|PHAssetResource" .
rg "Service\\.shared|let .*Service|var .*Service|: .*Service|= .*Service\\(" .
rg "XPhotoKit" .
```

## Review 结论写法

- 对非 `class` 的 Service，说明“Service 类型必须声明为 `class`，当前用 `struct` / `enum` / `actor` 承载”，并建议改为 `final class XxxService`，由 Manager 注入持有。
- 不要输出「Service 应遵守 `Sendable`」「Service 应改成 `actor` 以满足并发安全」这类结论；本项目 Service 不要求 `Sendable`。
- 对直接 PhotoKit 调用，说明“业务侧绕过 XPhotoKit 调用照片底层能力”，并建议补 XPhotoKit Service 能力。
- 对 Service 依赖 Service，说明依赖方式、被依赖 Service、影响范围，并建议把编排上移到 Manager。
- 对 Service 内数据处理，说明“Service 函数承担了调用前数据处理，违反 Service 只接收已处理数据并执行服务调用的铁律”，并建议把处理逻辑移到外部合适层级。
- 对 Service 重复能力，说明“Service 中存在重复能力，多个函数语义相近但各自做同源底层调用”，列出重复函数及差异点，并建议合并为同一函数（参数化/可选参数/集合入参/枚举区分）。
- 对 Service 重复 private helper，说明“新增 private helper 与现有 helper 承担同语义基础处理，仍属于 Service 重复能力”，列出新增 helper 和已有 helper，建议复用或抽到事务可复用的稳定入口。
- 如果只是 XPhotoKit 能力缺口，不要建议在业务 Service 中临时复制逻辑；应明确指出需要补 XPhotoKit。
