---
name: git-commit
description: Use when the user asks to generate a git commit with message in Chinese for the current changes
---

# Git Commit

## Overview

1. 根据修改内容提交一个git commit
2. 为这个commit生成一个中文的 `git commit message`。

## Commit Format

格式：

```text
{emoji前缀}{归属项目}: {修改描述}
```

示例：

```text
✨ Photos: 添加了一个新功能
```

## Emoji Prefixes

| Emoji | 类型 | 说明 |
| --- | --- | --- |
| ✨ | `feat` | 新功能 |
| 🐛 | `fix` | 修复 bug |
| 🛠️ | `refactor` | 代码重构，不新增功能、不修 bug |
| ⚡️ | `perf` | 性能优化 |
| 🔥 | `remove` | 删除代码或文件 |
| 🎨 | `style` | 代码格式调整，不影响逻辑 |
| 📚 | `docs` | 更新文档 |
| 📝 | `docs` | 修改注释或 README |
| 🔧 | `chore` | 配置修改、工具链调整 |
| 🔨 | `build` | 构建相关变更，如 CI/CD、脚本 |
| 🧪 | `test` | 增加或修改测试 |
| 📦 | `deps` | 添加或移除依赖 |
| ⬆️ | `deps` | 升级依赖 |
| ⬇️ | `deps` | 降级依赖 |
| 🚀 | `deploy` | 部署或发布 |
| 🔖 | `release` | 版本标签 |
| 💡 | `comment` | 增加或修改注释 |
| 🔒 | `security` | 安全修复 |
| 🗑️ | `delete` | 删除文件 |
| 📁 | `move` | 移动文件或重命名 |

## Constraints

- `commit message` 必须使用中文。
