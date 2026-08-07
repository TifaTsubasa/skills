---
name: buddy-log-api-query
description: Use when querying Buddy archived remote logs through the local HTTP API on 127.0.0.1:9124.
---

# buddy-log-api-query

## Overview

Use Buddy's local HTTP API to query archived remote structured logs.

Always probe `/health` first. If it is unreachable, tell the user clearly:

> 先启动 Buddy。

Do not use this skill for:

- macOS unified logging
- Xcode build logs
- non-Buddy apps
- Buddy Web debug memory snapshots

## Default Workflow

1. Check service health:

```bash
curl -sf http://127.0.0.1:9124/health
```

2. If health succeeds, choose the time range:

- Prefer `last` for quick inspection
- Prefer `from` + `to` for reproducible analysis

3. Add only needed filters:

- `level`
- `sessionId`
- `subsystem`
- `category`
- `process`
- `query`
- `limit`

4. Read the JSON in this order:

- `summary.totalMatched`
- `summary.returnedCount`
- `summary.truncated`
- `summary.skippedMalformedLines`
- `entries`

## Common Commands

Health:

```bash
curl -s http://127.0.0.1:9124/health | jq
```

Recent logs:

```bash
curl -s 'http://127.0.0.1:9124/v1/logs/query?last=15m&limit=50' | jq
```

Recent errors:

```bash
curl -s 'http://127.0.0.1:9124/v1/logs/query?last=1h&level=error&limit=100' | jq
```

Single session:

```bash
curl -s 'http://127.0.0.1:9124/v1/logs/query?last=1h&sessionId=run-123&limit=100' | jq
```

Subsystem + keyword:

```bash
curl -s 'http://127.0.0.1:9124/v1/logs/query?last=2h&subsystem=photos.receiver&query=failed&limit=100' | jq
```

Absolute range:

```bash
curl -s 'http://127.0.0.1:9124/v1/logs/query?from=2026-04-21T10:00:00Z&to=2026-04-21T11:00:00Z&limit=100' | jq
```

## Interpretation Rules

- Empty `entries` with HTTP `200` is still a successful query.
- If `summary.truncated` is `true`, narrow the window or raise `limit` up to `1000`.
- If `summary.skippedMalformedLines` is greater than `0`, the archive had damaged lines but valid lines were still returned.
- `sessionId` is the API name for upstream `runId`.

## Reference

Read the full API document here:

`/Users/yuri/Desktop/workspaces/ios/Buddy/docs/reference/buddy-log-query-api.md`
