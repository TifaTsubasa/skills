# Localizable.xcstrings 精确 JSON 模板

Xcode 15+ 的 String Catalog 格式。**这个 reference 是写入 xcstrings 时的唯一参考**：模板里没出现的字段不要乱加。

## 文件骨架

```json
{
  "sourceLanguage" : "en",
  "strings" : {
    "<key>" : { ... },
    "<key>" : { ... }
  },
  "version" : "1.0"
}
```

- `sourceLanguage` 是 `"en"`（本项目固定，**不要**改）。即使翻译时基准文案是中文，sourceLanguage 字段保持 en。
- `strings` 是对象，key 是字符串 key，value 是「条目对象」。
- `version` 固定 `"1.0"`。

## 普通字符串条目（无复数）

```json
"<key>" : {
  "extractionState" : "manual",
  "localizations" : {
    "en" : {
      "stringUnit" : {
        "state" : "translated",
        "value" : "Delete Selected"
      }
    },
    "zh-Hans" : {
      "stringUnit" : {
        "state" : "translated",
        "value" : "删除选中"
      }
    },
    "zh-Hant" : {
      "stringUnit" : {
        "state" : "translated",
        "value" : "刪除選取"
      }
    },
    "ja" : {
      "stringUnit" : {
        "state" : "translated",
        "value" : "選択項目を削除"
      }
    },
    "ko" : {
      "stringUnit" : {
        "state" : "translated",
        "value" : "선택 항목 삭제"
      }
    }
  }
}
```

- `extractionState` 用 `"manual"`（手动添加的 key 都是 manual）。Xcode 自动扫描出来的会是 `"extracted_with_value"`，本 skill 不生成那种。
- 语言顺序：**en → zh-Hans → zh-Hant → ja → ko**。和现有文件保持一致，方便 diff。
- `state` 用 `"translated"`。**不要**用 `REVIEWED`（那是人审过的状态）、`needs_review`、`stale`。

## 复数条目（带 plural variations）

只有英语写 `one + other`，其它 4 种只写 `other`：

```json
"<key>" : {
  "extractionState" : "manual",
  "localizations" : {
    "en" : {
      "variations" : {
        "plural" : {
          "one" : {
            "stringUnit" : {
              "state" : "translated",
              "value" : "%lld photo selected"
            }
          },
          "other" : {
            "stringUnit" : {
              "state" : "translated",
              "value" : "%lld photos selected"
            }
          }
        }
      }
    },
    "zh-Hans" : {
      "variations" : {
        "plural" : {
          "other" : {
            "stringUnit" : {
              "state" : "translated",
              "value" : "已选中 %lld 张照片"
            }
          }
        }
      }
    },
    "zh-Hant" : {
      "variations" : {
        "plural" : {
          "other" : {
            "stringUnit" : {
              "state" : "translated",
              "value" : "已選取 %lld 張照片"
            }
          }
        }
      }
    },
    "ja" : {
      "variations" : {
        "plural" : {
          "other" : {
            "stringUnit" : {
              "state" : "translated",
              "value" : "%lld枚の写真を選択中"
            }
          }
        }
      }
    },
    "ko" : {
      "variations" : {
        "plural" : {
          "other" : {
            "stringUnit" : {
              "state" : "translated",
              "value" : "사진 %lld장 선택됨"
            }
          }
        }
      }
    }
  }
}
```

注意：

- 英语 `one` 写「单数」文案，`other` 写「复数」文案，**不能两个写一样的**（否则等于没做复数处理）。
- 中日韩这 4 种语言**只写 `other` 一个变体**。Apple 允许：CLDR 规则里这些语言只有 `other` 一种复数分类。**不要**写 `one` 字段，会让文件冗余且和本项目惯例不符。
- `variations.plural.<one|other>.stringUnit` 三层嵌套必须齐全，少一层 Xcode 就解析失败。

## 占位符规则

- 源里是 `%lld`，所有译文都用 `%lld`。源里是 `%d`，都用 `%d`。**不混用**。
- `%@` 是 `NSString` / Swift `String` 插值。
- `%lf`、`%.2f` 是浮点。
- `%@` 出现在中文里通常不需要复数变体（除非语义就是数量）。
- 多个占位符可以用位置参数 `%1$@`、`%2$lld`，译文调整语序时方便重排。**只在源文案已用位置参数时才用**，不要主动改写源里的简单 `%@`。

## state 字段值对照

| state            | 含义                          | 何时用                                        |
| ---------------- | ----------------------------- | --------------------------------------------- |
| `new`            | 新 key，尚无翻译              | 本 skill 不用                                 |
| `translated`     | 翻译已写入，尚未人工审核      | **本 skill 默认值**                           |
| `needs_review`   | 源文案变了，旧翻译需要再确认  | 本 skill 不主动写；偶尔在修订旧 key 时可用    |
| `REVIEWED`       | 人工审核通过                  | **本 skill 不写**，只有人在 Xcode 里点确认才写 |
| `stale`          | key 在代码里已不存在          | 本 skill 不用                                 |

## extractionState 字段值对照

| extractionState         | 含义                              | 何时用                |
| ----------------------- | --------------------------------- | --------------------- |
| `manual`                | 人在 xcstrings 里手写的 key       | **本 skill 默认值**   |
| `extracted_with_value`  | Xcode 编译扫描出来的 key          | 本 skill 不生成       |
| `stale`                 | 源代码里已删，xcstrings 还留着    | 本 skill 不生成       |

## 缩进与格式

- **2 空格缩进**（Xcode 序列化的默认）。
- key/value 之间是 `" : "`（冒号两边各一个空格）—— 这是 Apple 序列化的 JSON 风格，和标准 JSON 不同，但 `json.tool` / `jq` 都能解析。**保持这个风格**，diff 才干净。
- 字符串内的特殊字符要转义：`"` → `\"`，`\n` 保持 `\n`（实际写 `\n` 这两个字符），反斜杠 → `\\`。
- 文件以单个换行结尾。

## 校验命令

写入后必跑：

```bash
python3 -m json.tool <path>/Localizable.xcstrings > /dev/null && echo "OK"
```

或：

```bash
jq empty <path>/Localizable.xcstrings && echo "OK"
```

任何一个报错就立刻修。常见错误：

- 末尾多了逗号：`"value" : "..."},` 后面再没条目了。
- 引号没转义：`"value" : "Don't ..."` 没转义 `'` 是 OK 的（单引号不需要转义），但 `"value" : "He said "hi""` 就错了。
- key 重复：JSON 允许但 Xcode 行为未定义，**新加 key 前必须确认 key 不重复**。
