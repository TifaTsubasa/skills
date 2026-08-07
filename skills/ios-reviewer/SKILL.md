---
name: ios-reviewer
description: Manual-only iOS Swift code review skill. Use only when the user explicitly invokes $ios-reviewer or directly points to .codex/skills/ios-reviewer for an architecture-focused review report.
---

# iOS Reviewer

## 工作方式

先按代码审查姿态工作：优先指出具体问题、风险、行为回归和缺失测试，再给简短总结。不要默认修改代码，除非用户明确要求修复。

### 工作模式

- **指定范围模式**：用户指定文件、目录、模块、类型、PR diff、staged diff 或代码片段时，只审查用户指定范围。为理解调用链可以读取相关上下文，但 Findings 只针对指定范围内的问题输出。
- **默认变更模式**：用户没有指定代码范围时，审查当前 git 工作区和暂存区代码。必须同时查看 `git diff --name-only` 与 `git diff --cached --name-only`，合并后作为待审文件清单。
- 默认变更模式下如果待审文件清单为空，明确说明当前没有工作区或暂存区变更，并请求用户指定审查范围。
- 报告的 `Scope` 必须写明实际使用的是“指定范围模式”还是“默认变更模式”，以及对应文件、目录或变更来源。

审查时必须：

- 先确认 Review 范围：用户指定文件、目录、模块、类型或变更集时，只审查指定范围；用户未指定范围时，默认审查 git 工作区变更和暂存区变更。
- 先阅读当前目录的 `AGENTS.md`、相关文件头部 `Rules` 注释，以及项目内架构文档或已触发的架构 skill。
- 使用 `rg` 查找相关类型、依赖注入点、属性持有关系、初始化链路和调用链。
- 只基于源码证据下结论；没有编译或运行时，说明结论是源码审查结果。
- 对每条 review case 增加短 hash 形式的 `case id`，优先基于文件路径、行号和问题标题生成，保证同一问题复查时稳定。
- 对每条问题按三部分输出：case id / 等级 / 标题、问题描述、改进方向。
- 按严重程度排序：`P0` 阻断或数据破坏，`P1` 明确架构违规或高风险，`P2` 可维护性/职责边界问题，`P3` 风格或补充建议。

### Review 范围

必须在开始审查前确定范围：

- 用户明确指定范围时，进入指定范围模式，按用户范围审查，例如某个文件、目录、模块、类型、PR diff 或 staged diff。
- 用户没有指定范围时，进入默认变更模式，默认使用 git 工作区变更和暂存区变更作为审查范围。
- 默认范围需要同时查看 `git diff --name-only` 与 `git diff --cached --name-only`，合并后作为待审文件清单。
- 如果默认范围为空，明确说明当前没有工作区或暂存区变更，并请求用户指定审查范围。
- 报告中必须写清楚实际审查范围，避免把局部审查表述成全项目结论。

## 分层规则

按 `references/architecture.md` 的 Page / Controller / Manager / Service / Store / View / Model / Util 分层规范审查，先审查底层 Service，再审查 Manager。发现跨层问题时，同时说明违规发生的位置和被依赖对象。

如审查范围涉及 Service 新增、Service 重构、PhotoKit/Photos.framework 调用、XPhotoKit 能力边界或 Service 编译问题，必须先阅读 `references/service.md`。

如审查范围涉及 Manager 新增、Manager 重构、Manager 函数职责或 Manager 数据整合逻辑，必须先阅读 `references/manager.md`。

如审查范围涉及 SwiftUI / UIKit View、ContentView、Cell 或 Component 职责，必须按下方 View 规则检查其是否保持纯视图。

任何审查开始前都必须先阅读 `references/common.md`，其中的通用编码约束（如 `uniqueKeysWithValues` 禁用、每个 Swift 文件最多一个顶层类型等）适用于所有层级，不限于特定变更类型。

### View

View 是纯 UI 组件层，负责把外部状态渲染成界面，并把交互意图交回上层。

必须检查：

- View 应该是纯状态驱动渲染的，然后通过回调向外通知事件。

### Service

Service 是单一领域的底层能力封装，详细规则见 `references/service.md`。

必须检查：

- **Service 类型必须声明为 `class`（`final class XxxService`）**，不允许用 `struct` / `enum` / `actor` 承载；由 Manager 依赖注入持有。
- **Service 不需要遵守 `Sendable`**：不得因为缺少 `Sendable` / `@unchecked Sendable` 输出 review case，也不得建议改成 `actor` 来满足并发安全；确有跨隔离域共享风险时写入 `Open Questions`。
- 其余单一职责、Service 不依赖 Service、只接收已处理数据等约束按 `references/service.md` 执行。

### Model

Model 是三层数据模型层（Entity / Item / Node），命名必须自解释所属层级。

必须检查：

- **模型类型名必须带明确的 `Entity` / `Item` / `Node` 后缀。** 出现 `Project`、`ProjectModel`、`ProjectData`、`ProjectInfo`、`ProjectDTO`、`ProjectVO`、`ProjectViewModel` 这类无后缀或自造后缀的模型时直接判为违规，要求重命名为 `ProjectEntity` / `ProjectItem` / `ProjectNode`。
- 同一业务的三层模型必须共用同一业务名前缀，只有后缀不同；跨层前缀不一致要输出 review case。
- 后缀必须与实际职责一致：持久化模型 `Entity`、Service ↔ Store 流转的业务模型 `Item`、Store `@Published` 暴露给 View 的渲染模型 `Node`；命名与职责错配（如 `Node` 里塞业务逻辑、`Item` 直接绑定 View）同样判为违规。
- Event / Command、Util、请求参数与配置类型不属于 Model 层，不要求也不应套用这三个后缀。

典型证据搜索：

```bash
rg "^\\s*(public |internal )?(final )?(struct|class|@Model final class) \\w*(Entity|Item|Node)\\b" .
rg "^\\s*(public |internal )?(final )?(struct|class) \\w*(Model|Data|Info|DTO|VO)\\b" .
```

### Util

Util 是纯同步数据处理层，只承载无状态、无副作用的纯函数式能力。

必须检查：

- **Util 类型必须声明为 `struct`，不允许用 `enum` 承载。** 看到 `enum XxxUtil`（含无 case 的「命名空间 enum」写法）时直接判为违规，要求改成 `struct XxxUtil`；该规则同样适用于 `ManagerUtil`、域内 Util 等所有以 Util 结尾的工具类型。
- Util 不持有任何状态，能力以 `static` 纯函数暴露，给定输入即得稳定输出。
- Util 只能依赖系统库和 Model，不能依赖 Manager / Service / Store / UI。
- Util 必须放在 `Packages/<XxxCore>/Sources/<XxxCore>/Utils/` 下，并在包内配套单元测试。

典型证据搜索：

```bash
rg "^\\s*(public |internal |private |fileprivate )?(final )?(enum|struct|class|actor) \\w*Util\\b" .
```

### Manager

Manager 是业务编排层，负责协调 Service 完成复杂任务，并向上提供业务语义清晰的能力。

必须检查：

- Manager 只能持有 Service，不能持有其他 Manager。
- Manager 主要负责编排、协调、调度 Service，可以承接轻量参数组装、单个返回值判断、简单默认值补齐等简单服务调用前后处理。
- Manager 不应直接承担数据库、网络请求、文件系统、PhotoKit 原始遍历、图像算法、缓存/重试/分页/权限/资源读取等复杂或可复用的服务处理；这类能力应下沉到 Service。
- Manager 可以维护业务级内存状态、任务生命周期、缓存索引和 Store 需要的聚合结果，但这些状态应服务于编排和 UI 刷新，而不是替代 Service 做底层能力。
- Manager 函数的能力边界必须符合 `references/manager.md` 中的数据获取与整合规则。

典型证据搜索：

```bash
rg "class .*Manager|struct .*Manager|actor .*Manager|protocol .*Manager" .
rg "let .*Manager|var .*Manager|: .*Manager|= .*Manager\\(" .
rg "let .*Service|var .*Service|: .*Service|= .*Service\\(" .
```

## Review 报告格式

如果发现问题，按以下格式输出：

```markdown
**Scope**
- 本次审查的文件、目录或变更来源。

**Findings**
- case: `<短hash>` `P1` 问题标题
  问题描述：说明违反了哪条规则、源码证据是什么、可能造成什么影响。
  改进方向：给出建议改法，说明应移动到哪个层级或如何调整调用关系。

**Open Questions**
- 只列需要用户确认的架构意图或业务边界；没有则写“无”。

**Summary**
- 简短总结审查范围和主要结论。

**Verification**
- 说明本次是否仅做源码审查，是否运行了编译或测试。
```

如果没有发现问题，明确写“未发现 Service/Manager/View 分层违规”，并补充仍未覆盖的范围或未运行的验证。
