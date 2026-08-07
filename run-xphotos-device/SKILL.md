---
name: run-xphotos-device
description: Use this skill whenever the user asks to run, install, launch, or debug the Photos iOS app (XPhotos.xcodeproj) on a real iPhone/iPad, or to capture runtime logs/console output from a real device. Triggers on "跑真机"、"装真机"、"运行到真机"、"真机调试"、"真机日志"、"device console"、"devicectl launch"、"debug on device"、以及任何明确要求真机（非模拟器）运行或取日志的场景。默认真机是 `SuperLuckyGoose` (UDID `543F1233-FFDA-5E37-9060-F0EDFAF83A5E`)，默认 scheme 是 `XPhotos`，默认 bundle id 是 `com.mkdir.photos.debug`。
---

# Run XPhotos on Device

## Overview

在真机上构建 / 安装 / 启动 `XPhotos`，并通过 `xcrun devicectl ... --console` 拿到启动后的 stdout/stderr 供调试。

典型用户意图：
- “跑到真机”“装到我手机”“真机启动一下”
- “真机日志看看”“真机 console 抓一下”
- “真机崩溃复现”“真机调试这个流程”

**技能边界**：只要目标是真机，就走这个技能。单元测试编写和验证走 `tdd`；组合场景（例如“真机装完再抓日志”）天然由同一条 `devicectl ... launch --console` 命令覆盖，不需要再切技能。

## 统一前提

- 工程：`XPhotos.xcodeproj`
- Scheme：`XPhotos`
- Debug bundle id：`com.mkdir.photos.debug`
- Build configuration：默认 `Debug`，产物路径 `Build/Products/Debug-iphoneos/XPhotos.app`
- 默认真机：
  - Name：`SuperLuckyGoose`
  - UDID：`543F1233-FFDA-5E37-9060-F0EDFAF83A5E`
- 工作目录：始终在仓库根目录的 `Photos/` 子目录里执行 `xcodebuild`（这也是 `.claude/commands/photos/run.md` 的做法）

不要把 `Photos` 当 scheme（历史遗留，已废弃），也不要用 workspace 形式。

## Default Flow

一条链路跑完：**选设备 → build → 定位 `.app` → install → launch（带 console）**。

```bash
# 1) build（带 provisioning 自动更新；destination 必须是真机）
cd Photos
xcodebuild \
  -project XPhotos.xcodeproj \
  -scheme XPhotos \
  -destination 'platform=iOS,name=SuperLuckyGoose' \
  -allowProvisioningUpdates \
  build

# 2) 定位刚产出的 .app（挑最近一次 Debug-iphoneos）
APP_PATH="$(ls -dt ~/Library/Developer/Xcode/DerivedData/XPhotos-*/Build/Products/Debug-iphoneos/XPhotos.app | head -n 1)"

# 3) 安装到真机
xcrun devicectl device install app \
  --device 543F1233-FFDA-5E37-9060-F0EDFAF83A5E \
  "$APP_PATH"

# 4) 启动并附带 console 流（这一步同时完成“运行”和“取日志”）
xcrun devicectl device process launch \
  --console \
  --device 543F1233-FFDA-5E37-9060-F0EDFAF83A5E \
  com.mkdir.photos.debug
```

第 4 步是阻塞式的：只要进程不退出，stdout / stderr 就会持续打到当前终端。要停就 `Ctrl-C` 或让用户手动退出 app；不要自己 `kill` 进程，否则用户看不到后续崩溃栈。

## Device Fallback

当默认设备不在线（`devicectl` 报 `The specified device was not found` 或 `xcodebuild` 找不到 destination）时，改走动态发现：

```bash
xcrun devicectl list devices
```

处理原则：
1. **不要自己挑一台设备静默继续**。把可用真机列表原样展示给用户，让他指定用哪台。
2. 用户选定后，用新的 name 替换 `-destination 'platform=iOS,name=<NAME>'`，用新的 UDID 替换 `--device <UDID>`，其余步骤不变。
3. 如果只列出了模拟器或连接的 Mac，明确告诉用户“没发现可用真机，需要连线/解锁/信任”而不是回退到模拟器。

## 常见失败与快速定位

- **Provisioning / 签名失败**：第一条 `error:` 通常是 "No profiles for 'com.mkdir.photos.debug' were found" 或 "Failed to register bundle identifier"。先把第一条报错原样贴出来，再让用户确认 Xcode 登录和设备 trust 状态，不要盲目清 DerivedData。
- **安装失败 `ApplicationVerificationFailed`**：绝大多数是设备没信任开发者证书，让用户去 *设置 → 通用 → VPN 与设备管理* 手动信任；别试着删除沙盒或重装系统。
- **`devicectl` 找不到设备**：先看线，再看 *设置 → 隐私 → 开发者模式* 是否开启；`xcrun devicectl list devices` 看不到就是没配对成功。
- **`.app` 找不到**：`DerivedData` 下 `XPhotos-*` 可能有多个（不同 user/branch），用 `ls -dt` 取最新；也可以显式传 `-derivedDataPath` 绕过。
- **Console 输出为空**：确认是真的启动到了前台（设备屏幕亮没亮、bundle id 有没有错）；`--console` 只抓被启动进程的 stdio，系统级日志要另走 `log stream --device`，不在本技能覆盖范围。

## 汇报格式

跑完一条链路后，按下面三段汇报：

- **Build**：成功 / 失败；失败则给出第一条 `error:` + 涉及文件
- **Install**：设备 name + UDID + 安装的 `.app` 路径
- **Launch**：进程 pid（`devicectl launch` 会打印）+ bundle id + console 是否开始出日志（给出前几行样例，别整段贴）

日志长时间无输出或用户明确表示“看够了”，再收手 —— 不要一启动就立刻断开，否则整个调试流程就废了。
