# Verify Tests

用于按 Photos 测试金字塔运行最小相关测试验证。优先跑与改动直接相关的子集，只有用户要求或风险较大时再扩大范围。

## 先判断验证层级
| 目标代码 | 测试层级 | 验证命令 |
| --- | --- | --- |
| Model / Util / Store | 单元测试 | `PhotosCoreTests` |
| Service / Manager | 集成测试 | `integration-tests` |
| Controller / ViewController / Page | 自动化测试（e2e） | 当前跳过 |

## 单元测试命令：PhotosCoreTests
```bash
xcodebuild test -project XPhotos.xcodeproj -scheme PhotosCoreTests -testPlan PhotosCoreTests -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

只验证单个测试类或方法时，在命令后追加：
```bash
-only-testing:PhotosCoreTests/<TypeName>
-only-testing:PhotosCoreTests/<TypeName>/<methodName>
```

## 集成测试命令：integration-tests
```bash
xcodebuild test -project XPhotos.xcodeproj -scheme XPhotos -testPlan UPhotos -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:integration-tests
```

只验证单个集成测试类或方法时，在命令后追加：
```bash
-only-testing:integration-tests/<TypeName>
-only-testing:integration-tests/<TypeName>/<methodName>
```

## 自动化测试：当前跳过
- Controller / ViewController / Page 的验证属于 e2e 自动化测试层。
- 当前项目明确不对这些内容进行测试；遇到这类改动时，在汇报中说明已按约定跳过测试要求。

## 执行规则
- 始终在仓库根目录执行命令。
- 默认使用 `iPhone 17 Pro`；设备不可用时先跑 `xcrun simctl list devices available`，再把 destination 换成实际可用模拟器。
- RED 阶段只需要跑最小相关测试；GREEN 阶段至少重跑同一命令确认通过。
- 如果失败，先定位第一条 `error:` 或第一个 failing test，不要整段日志回贴。
- 不用 `swift test` 替代 PhotosCore 的 `xcodebuild test`，因为这里要验证主工程集成路径。

## 汇报内容
- 命中的测试层级
- 执行的完整命令；如果 e2e 跳过，说明跳过原因
- 通过 / 失败
- 失败用例名
- 第一条关键错误
