# Write Tests

用于在 Photos 项目里按测试金字塔编写或调整测试。目标是先用测试描述行为，再写最少实现让测试通过。

## 先判断测试层级
| 目标代码 | 测试层级 | 测试位置 | 处理方式 |
| --- | --- | --- | --- |
| Model / Util / Store | 单元测试 | `Packages/PhotosCore/Tests/PhotosCoreTests/` | 编写 Swift Testing 单测 |
| Service / Manager | 集成测试 | `integration-tests/` | 编写 Swift Testing 集成测试 |
| Controller / ViewController / Page | 自动化测试（e2e） | 当前不落地 | 明确跳过，不补测试 |

## TDD 顺序
- 先写一个最小失败测试，测试名描述业务行为而不是实现细节。
- 运行最小相关测试并确认 RED：失败原因必须是目标行为缺失，不是拼写、导入、编译错误或测试夹具错误。
- RED 正确后再改生产代码；如果已经先写了实现，先提示用户这不是严格 TDD，再按用户指令继续。
- GREEN 后只做必要清理，不顺手重构无关代码。

## 单元测试：Model / Util / Store
- 放在 `Packages/PhotosCore/Tests/PhotosCoreTests/` 下，按 `Store/`、`Model/`、`Utils/` 等现有目录归类。
- Store 测试覆盖 Event → Command 批次调度、Event → State 状态计算。
- Util 测试覆盖纯同步数据处理：转换、过滤、聚合、计算、规则判定、格式化。
- Model 测试只覆盖 Item / Node 中真实存在的业务逻辑；纯字段模型不为了覆盖率硬写测试。
- 异步 Store 测试沿用现有 `CommandRecorder` / `waitFor...` 模式，先等待命令流稳定再断言。

## 集成测试：Service / Manager
- 放在 `integration-tests/` 下，按现有 `database/`、`biz/` 或业务目录归类。
- Manager / Service 测试验证真实协作边界、持久化、缓存、系统服务适配或多对象组装，不把纯同步计算留在 Manager / Service 里测。
- 如果测试暴露出纯同步加工逻辑，应提示把逻辑下沉到 PhotosCore Util，并改写为单元测试覆盖。
- 不把 Event / Command 当作 Manager / Service 的内部协作接口；它们只属于 Store ↔ Controller 边界。

## 自动化测试：Controller / ViewController / Page
- 这层属于 e2e 自动化测试范围，当前明确不落地。
- 遇到只改 Controller、ViewController 或 Page 的任务时，说明“当前跳过该层测试要求”，不要补单元测试或集成测试来模拟高层 UI 编排。

## 编写规则
- 新增测试使用 Swift Testing：`import Testing`、`@Test("中文行为描述")`、`#expect(...)`、`Issue.record(...)`。
- 每个测试只覆盖一个行为；测试名和 `@Test` 文案都要能看出输入、动作和期望。
- 测试辅助函数、辅助类型也要有一行中文注释；模型和属性遵守项目注释规则。
- 避免只验证 mock 被调用；优先验证状态、返回值、事件、命令、持久化结果或服务协作结果。

## RED 记录
写完测试后进入验证模式，运行最小相关命令。向用户汇报时明确：
- 命中的测试层级
- 测试文件和测试名
- RED 是否出现
- 第一条失败原因
