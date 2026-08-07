---
name: update-release-notes
description: Use when updating App Store release notes in fastlane metadata from a Chinese change summary, especially when the notes must be translated into each locale's language and confirmed before writing files
---

# Update Release Notes

用于根据中文更新说明，生成并更新 `fastlane/metadata/*/release_notes.txt`。

## 何时使用

- 用户要求根据中文内容更新 App Store 发布说明
- 用户提到 `release_notes.txt`、`fastlane metadata`、`metadata`、`发布说明`
- 需要把中文翻译成各语言目录对应的语言

## 核心规则

- 始终以仓库中的 `fastlane/metadata` 为根目录，不使用 `fastlane/fastlane/metadata`
- 始终先预览，明确得到用户确认后才写文件
- 语言目录以实际存在的 `fastlane/metadata/<locale>/release_notes.txt` 为准
- 文案风格默认使用 App Store 发布说明风格：自然、简洁、面向用户，不做逐字直译

## 执行流程

1. 读取中文更新描述。如果用户还没提供，就先索取中文内容。
2. 扫描当前仓库里的目标语言：

```bash
python3 .codex/skills/update-release-notes/scripts/update_release_notes.py list-locales
```

3. 为每个 locale 生成候选文案：
   - `zh-Hans`：保留简体中文，可轻微润色
   - `zh-Hant`：转换为自然繁体中文
   - `en-US`：翻译为自然英文
   - 其他 locale：按 locale 对应语言翻译；如果你无法可靠翻译，先明确标注风险，不要伪造高置信度结果
4. 将候选文案整理成一个 JSON 文件，格式如下：

```json
{
  "en-US": "What's new...",
  "zh-Hans": "本次更新：...",
  "zh-Hant": "本次更新：..."
}
```

5. 用脚本生成预览，向用户展示每个 locale 的旧内容和新内容差异：

```bash
python3 .codex/skills/update-release-notes/scripts/update_release_notes.py preview --translations-file /tmp/release-notes.json
```

6. 明确询问用户是否写入。只有在用户给出明确确认后，才执行：

```bash
python3 .codex/skills/update-release-notes/scripts/update_release_notes.py apply --translations-file /tmp/release-notes.json
```

## 输出要求

- 预览阶段：
  - 先列出将被更新的 locale
  - 再逐个展示旧内容和新内容
  - 明确说明“尚未写入文件”
- 写入阶段：
  - 列出实际写入的文件路径
  - 如果某些 locale 缺少翻译，明确列出哪些未写入

## 常见约束

- 不要修改 `release_notes.txt` 以外的 metadata 文件
- 不要假设固定语言集合，始终以目录扫描结果为准
- 若用户只想更新部分语言，先按用户要求过滤，再预览
- 若中文输入是要点列表，翻译后保留简洁列表风格；若是完整段落，保持段落风格
