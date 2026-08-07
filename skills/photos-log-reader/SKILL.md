---
name: photos-log-reader
description: Use when asked to read, tail, monitor, or debug the Photos iOS app log in real-time from the simulator. Triggers on requests like "看日志", "读日志", "查看日志", "tail log", "read log".
---

# Photos Log Reader

读取 Photos app（模拟器）实时日志。

## 获取日志路径

```bash
LOG="$(xcrun simctl get_app_container booted com.mkdir.photos.debug data)/Library/Caches/logs/xPhoto.log"
```

## 常用命令

**实时监控（tail）**
```bash
tail -f "$(xcrun simctl get_app_container booted com.mkdir.photos.debug data)/Library/Caches/logs/xPhoto.log"
```

**读取最近 N 行**
```bash
tail -n 100 "$(xcrun simctl get_app_container booted com.mkdir.photos.debug data)/Library/Caches/logs/xPhoto.log"
```

**过滤关键字**
```bash
tail -f "$(xcrun simctl get_app_container booted com.mkdir.photos.debug data)/Library/Caches/logs/xPhoto.log" | grep -i "error\|warning"
```

**读取全部日志（供 AI 分析）**
```bash
cat "$(xcrun simctl get_app_container booted com.mkdir.photos.debug data)/Library/Caches/logs/xPhoto.log"
```

## 注意

- 需要模拟器已启动且 app 运行过至少一次
- 多个模拟器同时运行时 `booted` 会返回其中一个；如需指定，替换为设备 UUID
- 轮转文件为 `xPhoto.log.1` ~ `xPhoto.log.4`，可用同样路径访问
