---
name: i18n-ios-edit
description: 把用户给的中文（或其它基准语言）APP 文案翻译成 en / zh-Hans / zh-Hant / ja / ko 五种语言，并以 Xcode `*.xcstrings` 的 JSON 结构精确写入项目文件，同时维护同名 Swift 访问层。遇到「帮我加几个文案」「翻译这条 key」「这些字符串补一下其它语言」「加个 i18n key」「xcstrings 里补一下英文/日文/韩文」「这段中文要在 App 里展示，给我对应的多语言」这类需求时主动触发；用户哪怕只给一段中文加 key 名，也应识别为本 skill 的工作场景。**不要**把翻译结果只丢在聊天里——只要用户意图是落到 App，就要写进 xcstrings 文件，并保证 JSON 合法。
---

# i18n-ios-edit

把用户给的中文文案翻译成五种语言并写入 `Photos/Resources/i18n/*.xcstrings`，再把 Swift 调用接到同名 Swift 访问层。**目标 = 落盘 + JSON 合法 + 代码可直接读取**，不是把翻译列在聊天里给用户。

## 0. 这个 skill 的两个 reference

- `references/xcstrings-format.md`：xcstrings 的精确 JSON 模板（普通字符串 / 复数变体 / 占位符），写入前必读。
- `references/translation-style.md`：5 种语言的 UI 文案风格、繁简差异、礼貌级别、文化雷区。翻译前必读。

每次开工前**都**读这两个文件，不要凭记忆。它们随项目迭代会更新。

## 1. 收齐输入

进入工作前必须明确三件事，缺一就在聊天里追问，不要硬猜：

1. **基准语言**：默认中文简体（zh-Hans）。如果用户给的明显是英文/日文，复述确认。
2. **key + 文案对**：拿到所有要翻译的条目。接受任意常见格式：
   - `empty_albums.delete_selected = 删除选中`
   - `- empty_albums.delete_selected: "删除选中"`
   - 直接贴一段 JSON
   - 甚至「key 叫 xxx，文案就是『删除选中』」这种口语描述
3. **目标 xcstrings 文件路径**：见第 2 节定位规则。没有显式路径时，按 key 前缀自动路由。

如果用户**只给文案、没给 key**：根据语义提一个建议 key（snake_case + 模块前缀，例如 `albums.delete_selected`、`timeline.arrange.finish`），让用户确认/修改，然后再继续。**不要默默自己起 key 写进去。**

## 2. 定位 xcstrings 文件与 Swift 访问层

按下面顺序找目标 catalog，找到唯一一个就直接用，不要追问：

1. 用户消息里已经提到的 `.xcstrings` 绝对/相对路径
2. key 以 `common.` 开头 → `Photos/Resources/i18n/Common.xcstrings`
3. key 属于设置 / IAP / 隐私权限域 → `Photos/Resources/i18n/Settings.xcstrings`，包括 `settings.*`、`paywall.*`、`pro_banner.*`、`early_price_alert.*`、`privacy_*`、`allow_access_photos`、`photo_permission_description`
4. 其它 App 文案 → `Photos/Resources/i18n/Localizable.xcstrings`
5. 项目根递归 `find . -name "*.xcstrings" -not -path "*/Pods/*" -not -path "*/.build/*"` 找到的唯一文件

找到 0 个或多个时，把候选列出来让用户选；不要选错一个就开始写。

每个 `.xcstrings` 旁边必须有一个同名 Swift 文件负责读取该 catalog：

- `Common.xcstrings` → `Common.swift`，通用文案统一走 `I18n.Common`。
- `Settings.xcstrings` → `Settings.swift`，设置、IAP、隐私权限文案统一走 `I18n.Settings`。
- `Localizable.xcstrings` → `Localizable.swift`，默认业务文案统一走 `I18n.Localizable`。

如果目标 Swift 文件不存在，先创建最小访问层；如果已存在，新增 key 时同步补访问属性或复用已有通用读取方法。迁到非默认 catalog 的 key，代码侧不能继续用裸 `String(localized:)` 默认表读取，必须改成对应访问层，例如 `I18n.Common.confirm`。
App target 的静态文案统一走同名 Swift 访问层：`I18n.Common.*`、`I18n.Settings.*`、`I18n.Localizable.*` 或对应 `text(_:)`，不要新增裸 `String(localized:)`、`NSLocalizedString`、`LocalizedStringKey("key")`、`Text("key")` 读取静态 key。

## 3. 判定是否是「复数 / 带占位符」

一条文案是否需要 `variations.plural`，按下面任意一条命中即视为复数：

- key 后缀含 `_format`、`_plural`、`_count`
- 文案里有 `%d`、`%lld`、`%@` 等占位符且语义上涉及数量（「%d 张照片」「Found %d ...」）
- 用户明说「这是个带数量的复数」

边界：

- 单纯 `%@` 表示插值字符串（如 `共释放 %@ 空间`）**不是**复数，按普通字符串处理。
- 占位符在中文里看着不像复数（`%d` 后无量词、纯计数）但语义是「N 个」时，英文照样要用复数 + `one/other`，要标为复数。
- **占位符必须 1:1 保留**：源文案用 `%lld` 译文也用 `%lld`，不要换成 `%d`；位置可调（不同语言语序不同），但个数和类型不能变。

不确定时一句话向用户确认：「这条 `xxx` 我按复数处理，英文会写 one/other 两条；要这样吗？」

## 4. 检查 key 是否已存在

写入前**必须**先在所有 `Photos/Resources/i18n/*.xcstrings` 里搜 `"<key>"`：

- **已存在于目标文件**：把现有翻译和你的新版列在聊天里，让用户选 overwrite / skip / 改 key。不要默默覆盖已 REVIEWED 的条目，会冲掉别人审核过的翻译。
- **已存在于其它 xcstrings**：先说明冲突位置，让用户确认是迁移、复用还是改 key。不要在两个 catalog 里重复写同一个 key。
- **不存在**：进入第 5 节。

## 5. 翻译

按 `references/translation-style.md` 的风格指南，把基准文案翻译成除基准语言外的 4 种。要点：

- **准确、简洁、贴合 UI**：按钮就是按钮（祈使/动名词），说明就是说明（完整句）。
- **长度尽量接近基准**：UI 空间敏感，能短就短，但准确性优先于长度。
- **占位符位置可调，但个数 / 类型一致**（见第 3 节）。
- **没有文化雷区**：避免地区敏感词、避免错用敬语级别、避免直译笑话/俚语。
- 复数条目：**只有英语**需要 `one / other` 两条不同文案；zh-Hans / zh-Hant / ja / ko 只写 `other` 一条（项目约定，本 xcstrings 已有的复数条目就是这种结构）。

如果某条文案在某语言下确实有歧义/无法准确翻译（例如双关、品牌名争议），在聊天里标出来，让用户决策，**不要硬翻**。

## 6. 写入 xcstrings

按 `references/xcstrings-format.md` 给出的精确模板拼装新条目，然后用 `Edit` 工具插入到目标 catalog 的 `strings` 对象里。

### 插入位置

- xcstrings 里的 key 不需要严格字母序（看现有文件就是大致按模块聚合）。
- 建议挑一个**模块前缀相同**的已有 key（例如要插 `empty_albums.xxx` 就找 `empty_albums.yyy`），插在它后面；找不到同模块前缀就插在文件末尾的 `}` 之前。
- `Edit` 的 `old_string` 取「上一个条目末尾的 `}` + 换行 + 下一个 key 起始的 `"xxx" : {`」做锚点，把新条目嵌进去；不要试图一次性重写整个文件。

### Swift 访问层

- 新增 `common.*` key 时，在 `Common.swift` 的 `I18n.Common` 里补一个有中文注释的静态属性。
- 新增设置 / IAP / 隐私权限域 key 时，在 `Settings.swift` 的 `I18n.Settings` 里补一个有中文注释的静态属性。
- 新增其它 key 时，在 `Localizable.swift` 的 `I18n.Localizable` 里补一个有中文注释的静态属性；确实需要动态 key 时再复用 `I18n.Localizable.text(_:)`。
- 修改 App target 调用点时，静态 key 必须走对应访问层；不要保留裸 `String(localized:)` 默认表读取，避免项目内出现两套风格。
- `Packages/PhotosCore` 这类包模块不能依赖 App target 的 `I18n.Settings`，迁到 `Settings.xcstrings` 后要用显式 table 读取，例如 `String(localized: "pro_banner.upgrade_to_pro", table: "Settings")`。
- Swift 文件里新增的每个类型、函数、属性都要有一行简明中文注释，遵守项目 AGENTS.md 约束。

### state 字段

- 新写入的条目 `extractionState` 用 `"manual"`（手动添加的 key，和文件里其它手写 key 一致）。
- 每条 `stringUnit` 的 `state` 用 `"translated"`（语义：翻译已完成、待人工 review。用户在 Xcode 里过一遍后会自动变 REVIEWED）。
- **不要**用 `REVIEWED`：那是人审过的状态，假的 REVIEWED 会污染审核流程。

### JSON 必须合法

写完后**强制**跑一次校验：

```bash
python3 -m json.tool <xcstrings 路径> > /dev/null
```

或者：

```bash
jq . <xcstrings 路径> > /dev/null
```

报错就立刻修复（常见：少了逗号、多了逗号、引号没转义、最后一个 key 后多了逗号）。**不修复完不交付。**

## 7. 交付清单

完成后，在聊天里简短给出：

1. ✅ 已写入 N 个 key 到 `<xcstrings 路径>`
2. 每个 key 列出 5 种语言的翻译，让用户扫一眼（特别是复数条目，让用户确认 one/other 文案）
3. 同名 Swift 访问层已同步，列出新增或复用的访问属性
4. 校验通过（贴出 `python3 -m json.tool` 的退出码或一句 "JSON 合法"）
5. **跳过的条目 / 让用户决策的条目**单独列出来

## 8. 反面例子

❌ **把翻译列在聊天里，没写文件**：违背 skill 的核心目的。
❌ **把 `common.*` 写回 `Localizable.xcstrings`**：通用文案应该进入 `Common.xcstrings`。
❌ **迁到 `Common.xcstrings` 后代码仍用裸 `String(localized:)`**：默认表找不到 key，会显示 key 本身。
❌ **App target 静态文案继续用 `Text("xxx.key")` / `String(localized:)`**：项目 i18n 使用风格不统一，后续拆 catalog 时容易漏改。
❌ **把设置 / IAP / 隐私权限域文案写回 `Localizable.xcstrings`**：这些文案应该进入 `Settings.xcstrings`。
❌ **`PhotosCore` 包里直接引用 `I18n.Settings`**：App target 的 Swift 文件不属于包模块，必须显式读取 `Settings` table。
❌ **复数条目英语只写 other**：英语 Xcode 会报错或退化显示。
❌ **复数条目中日韩写了 one + other 两条相同内容**：和本项目惯例不一致，让 reviewer 困惑。本项目约定中日韩只写 other。
❌ **占位符从 `%lld` 改成 `%d`**：和源代码 `String(format:)` 调用不匹配，运行时崩溃或显示错误。
❌ **默默覆盖已 REVIEWED 的翻译**：会冲掉同事审核过的成果。
❌ **写完不校验 JSON**：Xcode 打开就报错，整个 xcstrings 加载失败。
❌ **state 用 REVIEWED**：污染审核状态。
❌ **key 没和用户确认就自己起一个**：和代码里的字面量对不上，等于白翻。

## 9. 何时不用这个 skill

- 用户只是问「这句怎么翻」，没有要落到 App 的意图 → 直接回答，别动文件。
- 用户在写 Swift 代码、要建 `String(localized:)` 调用 → 那是代码侧，不是本 skill 范围（除非他同时让你加 key 到 xcstrings 或维护同名 Swift 访问层）。
- 用户要改 `Localizable.strings`（老的 plist 风格而非 xcstrings）→ 本 skill 不处理那种格式。
- 用户要改的是 InfoPlist 或 LaunchScreen 文案 → 那是 `InfoPlist.xcstrings` 等独立文件，不在本 skill 范围（除非用户指明也要改）。
