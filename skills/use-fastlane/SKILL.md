---
name: use-fastlane
description: Use this skill whenever working with the Photos iOS repo's fastlane toolchain — calling lanes (PhotosCore 测试 via fastlane、构建并上传 TestFlight/App Store、只传 metadata、只传截图) **或** 修改 `fastlane/` 下的内容（Fastfile / Appfile / Pluginfile / metadata 多语言文案 / screenshots）。Triggers on "跑 fastlane"、"fastlane lane"、"fastlane ios xxx"、"打包传 TestFlight"、"传 App Store"、"上传 metadata"、"传截图到 App Store"、"改 App Store 描述/副标题/关键词/名称"、"新增 / 修改 fastlane lane"、"改 Fastfile"、"fastlane 报错"、以及任何明确依赖 `fastlane/` 目录的场景。**边界**：①release_notes 的多语言翻译走 `update-release-notes`，本 skill 不动 `release_notes.txt`；②用户只说"跑 PhotosCore 单测"且没提 fastlane 时走 `test-photos-photoscore` 或 `tdd`，明确说"用 fastlane 跑 test_photoscore"才走本 skill；③真机运行走 `run-xphotos-device`，模拟器构建不属于本 skill。
---

# Use Fastlane

## Overview

`Photos/fastlane/` 是这个 iOS 工程对 App Store / TestFlight / PhotosCore 测试的统一入口。本 skill 覆盖两类需求：

1. **调用 lane**——执行 `fastlane ios <lane>` 跑测试、打包、上传
2. **修改 fastlane 内容**——改 Fastfile / Appfile / Pluginfile，或者编辑 `metadata/` 多语言文案、整理 `screenshots/`

两类需求经常混在一起（"加一个新 lane 然后跑一下""改 App Store 描述然后上传 metadata"），所以放在同一个 skill 里。

## 统一前提

- **仓库根目录**：`/Users/yuri/Desktop/workspaces/xstudio/ios/Photos/`（下文统称 `Photos/`）
- **工作目录**：所有 `fastlane` 命令一律在 `Photos/` 根目录下执行，**不要** `cd Photos/fastlane/` 再跑——fastlane 自己会找子目录
- **工程文件**：`XPhotos.xcodeproj`，主 scheme `XPhotos`
- **fastlane 根**：`Photos/fastlane/`（不是 `Photos/fastlane/fastlane/`，后者是测试输出目录）
- **App Identifier**：`com.mkdir.photos`（见 `Appfile`）
- **fastlane 版本要求**：≥ `2.229.1`（见 `Fastfile` 顶部 `fastlane_version`）

## 危险动作护栏（最重要的一条）

下面这些 lane 会**真的把构建产物或文案推到苹果服务器**，一旦执行就无法本地回滚：

- `fastlane ios beta` — 上传到 TestFlight + Sentry
- `fastlane ios release` — 上传到 App Store Connect（不自动提审，但已经占用版本号）
- `fastlane ios metadata` — 覆盖 App Store Connect 上的多语言文案
- `fastlane ios screenshots` — `overwrite_screenshots: true` 会清掉旧截图

**规则**：

1. 即使用户大致表达了"打包上传"的意思，**也要在执行前再次确认目标 lane、当前 git 分支、当前 build number / version**；得到明确确认（"好"/"跑"/"yes"）后才执行
2. 不要主动建议或顺手跑这些 lane，除非用户明说
3. `test_photoscore` / `test_photoscore_alternate` / `test_photoscore_swift` / `validate_photoscore` 是只读的，可以放心直接跑

## 现有 lane 清单

下表是 `Fastfile` 里现存的全部 lane。**只能用这个表里有的**，不要凭印象编 `fastlane ios deploy` 这种不存在的 lane（fastlane 会报错但浪费时间）。

| Lane | 危险等级 | 一句话 | 何时用 |
| --- | --- | --- | --- |
| `test_photoscore` | 只读 | xcodebuild 跑 PhotosCoreTests，默认 iPhone 17 Pro | 用户明确说"用 fastlane 跑 PhotosCore 测试" |
| `test_photoscore_alternate` | 只读 | 同上，备用设备 iPhone 14 | 默认设备模拟器没装时 |
| `test_photoscore_swift` | 只读 | 直接 `swift test --enable-code-coverage`，不经 xcodebuild | 想跳过 xcodebuild、直接走 SPM |
| `validate_photoscore` | 只读 | `swift package describe / show-dependencies` | 改了 `Package.swift` 想验证依赖图 |
| `beta` | 🔴 上传 TestFlight | 自增 build number → build_app → upload_to_testflight → 上传 Sentry debug 文件 | 用户明确要发 TestFlight |
| `release` | 🔴 上传 App Store | 同 beta 流程，但走 `upload_to_app_store`（不提审、不传截图/metadata） | 用户明确要传 App Store 二进制 |
| `metadata` | 🔴 覆盖商店文案 | 只传 metadata，不传二进制/截图，不提审 | 用户明确要把本地 `metadata/` 同步到商店 |
| `screenshots` | 🔴 覆盖商店截图 | 只传截图，`overwrite_screenshots: true` | 用户明确要把本地 `screenshots/` 同步到商店 |

### lane 之间的依赖关系

- `beta` 和 `release` 都会先调 `build_release_ipa!`：会 `increment_build_number` → `clean: true` 完整重编。**build number 一旦自增就回不去**（除非手工改 plist），所以失败重跑会再次 +1
- 上传部分都走 `upload_to_app_store_authenticated`：优先用 `APP_STORE_CONNECT_API_KEY_*` 环境变量做 JWT 鉴权；没设置 API Key 时回退到密码登录（`FASTLANE_USER` + 钥匙串里的 app-specific password），需要二次验证

## 调用 lane 的标准做法

```bash
# 始终在仓库根（Photos/）下执行
cd /Users/yuri/Desktop/workspaces/xstudio/ios/Photos

# 看现有 lane（怀疑文档过期或想确认 lane 名字时用）
fastlane lanes

# 只读类（不需要鉴权）
fastlane ios validate_photoscore
fastlane ios test_photoscore
```

### 需要鉴权的 lane：从 `~/.env` 加载认证

本项目约定把所有 App Store Connect / Apple ID 认证信息放在 `~/.env`，**不要把这些值打印或写进仓库**。运行任何需要鉴权的 lane（`beta` / `release` / `metadata` / `screenshots`）时，用 `set -a` / `source` / `set +a` 把变量加载到环境，再调用 fastlane。

**完整命令模板**（替换 `<lane>` 即可）：

```bash
set -a; source ~/.env; set +a; fastlane ios <lane>
```

各危险 lane 的完整调用（**执行前必须二次确认目标 lane、当前 git 分支、当前 build/version**）：

```bash
# 上传商店元信息（覆盖 5 个 locale 的所有 metadata 字段）
set -a; source ~/.env; set +a; fastlane ios metadata

# 上传截图（覆盖商店现有截图）
set -a; source ~/.env; set +a; fastlane ios screenshots

# 构建 + 上传到 TestFlight + 上传 Sentry dSYM（会自增 build number）
set -a; source ~/.env; set +a; fastlane ios beta

# 构建 + 上传到 App Store Connect（不自动提审，会自增 build number 并占用版本号）
set -a; source ~/.env; set +a; fastlane ios release
```

加载模式说明：
- `set -a` 让 `source ~/.env` 期间所有定义的变量自动 export，fastlane 子进程才能看到
- `set +a` 关闭自动 export，避免污染后续 shell
- 一条命令一次性加载，**不要**把它拆成两步执行（中间任何中断都让认证只剩一半）
- 如果想完全隔离当前 shell，外面包一层子 shell：`(set -a; source ~/.env; set +a; fastlane ios metadata)`

### 排错

加 `--verbose`：

```bash
set -a; source ~/.env; set +a; fastlane ios metadata --verbose
fastlane ios test_photoscore --verbose
```

dry-run 对比商店当前 metadata（**会覆盖本地未 commit 的 metadata 改动**，跑之前先 commit）：

```bash
set -a; source ~/.env; set +a; fastlane deliver download_metadata --skip_screenshots true --skip_binary_upload true
```

### 日志和产物位置

- **测试日志**：`Photos/fastlane/test_output/test_raw.log`（或 `test_alternate.log`）。`Fastfile` 里的 `summarize_test_log` 会扫描这个日志并打印通过 / 失败汇总；要看完整 stack 自己 `cat` 这个文件
- **构建日志**：`Photos/fastlane/build_logs/`
- **打包产物**：`Photos/fastlane/build/XPhotos.ipa`
- 这三个目录都被 `ensure_output_directories!` 自动创建，不存在时不要慌

### 失败处理

- 看日志先看**第一条** `error:` / `❌`，不要回贴整段日志
- 测试失败：先 `cat Photos/fastlane/test_output/test_raw.log` 找 `TEST FAILED`，再看具体 case
- 模拟器型号不可用：`xcrun simctl list devices available` 确认有哪些设备，再考虑是用 `test_photoscore_alternate`（iPhone 14）还是改 `Fastfile` 里的 `device_name`
- 上传鉴权失败：检查环境变量（见下一节）；不要主动改 `Appfile` 把账号写进去——账号信息只能从环境变量来

## 环境变量

`Appfile` 故意把账号留给环境变量，**不要把 Apple ID / Team ID 硬编码到 `Appfile`**。本项目把下面这些变量集中放在 `~/.env`，所有需要鉴权的 lane 都通过 `set -a; source ~/.env; set +a; fastlane ios <lane>` 加载（见上一节）。**不要 `cat ~/.env` 把内容打印出来**，也不要复制 `~/.env` 进仓库。

```bash
# 通用
export FASTLANE_USER=your_email@example.com   # Apple ID
export FASTLANE_TEAM_ID=your_team_id          # Developer Portal team
export FASTLANE_ITC_TEAM_ID=your_itc_team_id  # App Store Connect team

# 推荐：App Store Connect API Key（替代密码登录，免 2FA）
export APP_STORE_CONNECT_API_KEY_KEY_ID=XXXXXXXXXX
export APP_STORE_CONNECT_API_KEY_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
export APP_STORE_CONNECT_API_KEY_KEY_FILEPATH=/absolute/path/to/AuthKey_XXXXXXXXXX.p8
# 二选一（key 内容直接放进环境变量）：
# export APP_STORE_CONNECT_API_KEY_KEY="-----BEGIN PRIVATE KEY-----\n..."
# 可选：
# export APP_STORE_CONNECT_API_KEY_DURATION=1200   # 秒
# export APP_STORE_CONNECT_API_KEY_IS_KEY_CONTENT_BASE64=true
# export APP_STORE_CONNECT_API_KEY_IN_HOUSE=true

# CI 环境
export CI=true   # 触发 Fastfile 里的 setup_circle_ci
```

**优先级**：只要 `APP_STORE_CONNECT_API_KEY_KEY_ID` 非空，`app_store_connect_api_key_from_env`（`Fastfile` 90-123 行）就会用 API Key；没设置才回落到 `FASTLANE_USER` 密码登录。

### Sentry

`beta` lane 末尾会调用 `sentry_debug_files_upload`（org `xstudio-apps`、project `xphotos`、`include_sources: true`）。需要环境里有 `sentry-cli` 配置好的 auth token（`SENTRY_AUTH_TOKEN` 或 `~/.sentryclirc`）。`release` lane 也调用了同一个上传——上传 dSYM 是为了线上崩溃符号化。

## 修改 `fastlane/` 内容

### 文件分工

| 文件 | 改它的场景 | 不该改的场景 |
| --- | --- | --- |
| `fastlane/Fastfile` | 新增 lane / 改 lane / 抽公共方法 | 把账号或密钥硬编码进去 |
| `fastlane/Appfile` | 改 `app_identifier` 或公司名 | 把 Apple ID / Team ID 写死（必须留 ENV） |
| `fastlane/Pluginfile` | 新增 fastlane 插件 | 删除"自动生成"注释 |
| `fastlane/README.md` | **永远不要手改**——它由 `fastlane lanes` 自动生成 | — |
| `fastlane/commands.md` | 给开发者补充常用命令记忆，可以改 | 改成 lane 的真实文档（README.md 才是） |
| `fastlane/metadata/<locale>/*.txt` | 改 App Store 各语言文案（**release_notes.txt 除外**） | 修改 `release_notes.txt`（走 `update-release-notes`） |
| `fastlane/metadata/*.txt`（顶层，无 locale） | 改分类 / copyright | — |
| `fastlane/metadata/review_information/*.txt` | 改审核 demo 账号、联系方式 | 把真实测试账号明文提交到公开仓库 |
| `fastlane/screenshots/<locale>/*.png` | 替换/新增截图 | 改文件名格式（见下节） |

### 修改 Fastfile 的约定

1. **不要把秘密提交进去**——账号、密钥、token 全部从 ENV 读
2. 新增的 lane 必须加 `desc "中文描述"`，否则 README.md 自动生成的描述会是空
3. 共享逻辑抽成顶层 `def`（参考已有的 `build_release_ipa!`、`run_photoscore_xcodebuild_tests`、`app_store_connect_api_key_from_env`），别在每个 lane 里复制粘贴
4. 输出目录走已有的 `TEST_OUTPUT_DIR` / `BUILD_LOG_DIR` / `BUILD_OUTPUT_DIR` 常量，**不要写硬编码路径**
5. 上传相关 lane 一律走 `upload_to_app_store_authenticated`，复用 API Key 鉴权逻辑
6. `before_all` 里的 `setup_circle_ci if ENV["CI"]` 不要去掉——CI 跑测试依赖它
7. 改完 `Fastfile` 后**重新生成 README.md**：

```bash
cd /Users/yuri/Desktop/workspaces/xstudio/ios/Photos
fastlane lanes   # 顺带刷新 README.md
```

### 修改 metadata 的约定

**locale 列表**：实际以仓库为准，不要假设固定集合。当前是 `en-US`、`zh-Hans`、`zh-Hant`：

```bash
ls Photos/fastlane/metadata
```

**字段长度上限**（App Store Connect 的硬限制，超出会被上传时拒绝）：

| 字段文件 | 上限 | 备注 |
| --- | --- | --- |
| `name.txt` | 30 字符 | App 名称 |
| `subtitle.txt` | 30 字符 | 副标题 |
| `keywords.txt` | 100 字符（含英文逗号） | 逗号分隔，不要空格 |
| `promotional_text.txt` | 170 字符 | 不重新提审就能更新 |
| `description.txt` | 4000 字符 | 段落式 |
| `release_notes.txt` | 4000 字符 | **走 `update-release-notes` skill** |

每个文本文件末尾保留一个换行符（POSIX 风格），不要带 BOM。

**多语言一致性**：原则上改一个字段就要把所有 locale 都更新，避免 App Store 上不同地区文案前后矛盾。如果用户只想改部分语言，明确告诉用户哪些 locale 没动。

**顶层 metadata 文件**（不分语言）：

- `primary_category.txt` / `secondary_category.txt`：当前是 `UTILITIES` / `PHOTO_AND_VIDEO`，值必须用 fastlane / App Store Connect 认可的英文常量
- `*_first_sub_category.txt` / `*_second_sub_category.txt`：子分类
- `copyright.txt`：当前 `2025 MkdirStudio Inc.`，每年年初要更新

**review_information/**：

- `email_address.txt`、`first_name.txt`、`last_name.txt`、`phone_number.txt`：审核联系人，要保持有效
- `demo_user.txt`、`demo_password.txt`：演示账号；如果 App 有登录就必须填，否则审核会被拒
- `notes.txt`：给审核员的特殊说明

### 修改截图的约定

**命名格式**：`{index}_{DEVICE_TYPE}_{slot}.png`

- `index`：截图在该 locale × 设备类型下的排序（0 起步）
- `DEVICE_TYPE`：App Store Connect 设备分类常量，本仓库当前用：
  - `APP_IPHONE_65` — iPhone 6.5" / 6.7"（iPhone 11 Pro Max / 14 Pro Max 等）
  - `APP_IPAD_PRO_3GEN_129` — 12.9" iPad Pro 第三代+
- `slot`：通常与 `index` 一致（fastlane 的占位符）

示例（`fastlane/screenshots/zh-Hans/`）：

```
0_APP_IPHONE_65_0.png
1_APP_IPHONE_65_1.png
2_APP_IPHONE_65_2.png
3_APP_IPHONE_65_3.png
4_APP_IPHONE_65_4.png
0_APP_IPAD_PRO_3GEN_129_0.png
1_APP_IPAD_PRO_3GEN_129_1.png
2_APP_IPAD_PRO_3GEN_129_2.png
```

**尺寸**（按 App Store Connect 当前要求；不符合上传会被拒）：

- `APP_IPHONE_65`：1284 × 2778 或 1242 × 2688（竖屏）
- `APP_IPAD_PRO_3GEN_129`：2048 × 2732（竖屏）

**操作守则**：

1. 替换截图时**保留原文件名**，让 `index/slot` 对应不变；要重排顺序就同步改文件名前缀，不要留空号
2. 每个 locale 的同一设备截图数量要一致（否则会有空位）
3. 改完截图不会自动上传，必须显式跑 `fastlane ios screenshots`（属于危险动作，要二次确认）
4. 新增设备类型先去 App Store Connect 截图规范查 `DEVICE_TYPE` 常量，不要瞎编

### 修改 Pluginfile 的约定

1. 新增插件后必须运行 `bundle install` 或 `fastlane install_plugins` 把 Gemfile 同步更新
2. 插件版本号写死（`gem "fastlane-plugin-xxx", "~> 1.2"`），别用 latest，CI 会因为版本飘移突然报错
3. 加进来的插件要在 `Fastfile` 里**真正用到**，单纯加进 `Pluginfile` 没意义

## 跨 skill 边界

- **release_notes 多语言翻译** → `update-release-notes`（它会读 `fastlane/metadata/*/release_notes.txt`，做翻译预览，本 skill 不要插手）
- **直接 xcodebuild 跑 PhotosCore 单测**（不经 fastlane）→ `test-photos-photoscore` 或 `tdd`
- **真机运行 / 抓 console** → `run-xphotos-device`（fastlane 没有真机调试 lane）
- **模拟器 build / 装 / 跑 App** → 不属于本 skill；按用户任务另行选择运行或调试方式
- **App Store 商店页面优化（keywords 头脑风暴、竞品分析）** → `app-store-optimization`；本 skill 只负责把 ASO 的产出**落到 metadata 文件**里
- **App Store 提交前自检** → `app-store-preflight-skills`；它扫合规问题，本 skill 不重复

## 汇报格式

- **调用 lane**：执行了哪个 lane、退出码、关键日志路径；危险 lane 还要给 build number / 上传目标
- **修改 fastlane 内容**：列出改了哪些文件、改前改后的关键差异、是否要后续运行某个 lane 来真正生效
- **报错**：第一条 `error:` 原文 + 涉及文件 + 建议下一步；不要回贴整段 fastlane 输出
