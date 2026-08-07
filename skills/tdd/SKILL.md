---
name: tdd
description: Use when working in the Photos iOS repo to write or verify tests for Model, Util, Store, Service, or Manager code; route PhotosCore unit tests, integration-tests, and skipped e2e automation according to the project testing pyramid.
---

# TDD

## Overview
这是 Photos 项目的 TDD 测试金字塔技能，只覆盖“编写测试”和“运行测试验证”两个模式。进入任一模式后先读取对应 reference，再开始改代码或执行命令。

统一前提：
- 主 scheme：`XPhotos`（历史文档里的 `Photos` scheme 已废弃）
- 默认模拟器：`iPhone 17 Pro`
- 架构边界遵循 `best-ios`：Store / Util / Model 在核心 SPM，Manager / Service 在主工程集成层，Page / Controller / ViewController 属于更高层入口
- PhotosCore 单测目录：`Packages/PhotosCore/Tests/PhotosCoreTests/`
- 集成测试目录：`integration-tests/`

## Route: 选哪个模式

按用户意图匹配下表。命中后只读对应文件；如果用户同时要求“先写测试再跑验证”，按“编写模式 → 验证模式”顺序串行读取和执行。

| 意图 / 触发词 | 目标 | 要读的文件 |
| --- | --- | --- |
| “写测试”“补测试”“写单测”“写集成测试”“先加测试”“TDD 实现”“为这个 bug 写复现测试” | 按测试金字塔编写或调整测试 | `references/write-tests.md` |
| “跑测试”“跑单测”“跑集成测试”“跑 PhotosCoreTests”“跑 integration-tests”“验证测试”“准备跑测试验证” | 按测试金字塔运行最小相关验证 | `references/verify-tests.md` |

## 测试金字塔

| 代码层级 | 测试层级 | 测试位置 | 当前要求 |
| --- | --- | --- | --- |
| Model / Util / Store | 单元测试 | `Packages/PhotosCore/Tests/PhotosCoreTests/` | 必须写，并用 PhotosCore 单测验证 |
| Service / Manager | 集成测试 | `integration-tests/` | 必须写，并用 integration-tests 验证 |
| Controller / ViewController / Page | 自动化测试（e2e） | 暂无当前入口 | 当前不测试，跳过这部分代码的测试要求 |

## 边界
- 不处理单纯 build、安装到模拟器、启动 App、UI 手动验证或真机调试。
- Controller / ViewController / Page 的行为属于自动化测试（e2e）层；当前项目明确不对这些内容补测试，不要为了它们写单元测试或集成测试。
- 不用旧文档里的 `Photos` scheme。

## 汇报格式
- 编写：说明命中的测试层级、新增/修改的测试文件、覆盖的行为、是否已看见 RED。
- 验证：说明命中的测试层级、执行的命令、通过/失败结果、失败用例名和第一条关键报错。
