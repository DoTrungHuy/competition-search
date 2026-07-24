# 数据维护脚本

浏览器里的「刷新列表」只重新读取已经发布的 JSON，不会执行 Python 或访问外部赛事网站。

## 准备

```bash
python -m pip install -r requirements-scripts.txt
```

## 校内通知草稿

```bash
python scripts/fetch_campus_cxcy.py
```

脚本使用 `sources.yaml` 中的 CSS selector 读取完整标题、详情链接和发布日期，生成：

- `new`：生产数据中没有对应详情链接。
- `changed`：同一稳定 ID 或链接的关键信息发生变化。
- `duplicate`：生产数据或本轮结果已存在。
- `rejected`：命中基金、公示、获奖、讲座等排除规则。

输出位于 `scripts/out/draft_campus.json`，该目录不进入 Git。草稿必须人工补全品牌、赛程和资格后才能合并。

## 多源采集

各源都产出同结构草稿 `scripts/out/draft_*.json`，共用 `draft_common.py`：

```bash
python scripts/fetch_campus_cxcy.py   # 校内 cxcy（HTML）
python scripts/fetch_devpost.py       # Devpost（JSON API）
python scripts/fetch_mlh.py           # MLH 黑客松（SSR HTML）
python scripts/fetch_kaggle.py        # Kaggle（API，需 KAGGLE_USERNAME/KAGGLE_KEY）
python scripts/fetch_tianchi.py       # 天池（Playwright 渲染，建议本机跑）
```

天池源需先装 Playwright：

```bash
python -m pip install -r requirements-playwright.txt
python -m playwright install chromium
```

## DeepSeek 审核与合并

```bash
python scripts/review_drafts.py       # 审核所有 draft_*.json -> reviewed.json（需 DEEPSEEK_API_KEY）
python scripts/apply_reviewed.py      # 合并进生产数据；对不上品牌时按提议自动建品牌
```

赛程策略（源优先 + 模型补充）：

1. 采集草稿若已有 `source_schedule_text` / `deadline` / 结构化日期，审核阶段**直接解析采用**。
2. 没有源日期时，DeepSeek 仅从线索提取；**仅 `schedule_confidence=high` 才写入**。
3. `apply`：有合法赛程且有深链接 → `needs_review=false`；否则待核验且不写公开赛程字段。

## 本机一键全流程

```bash
python scripts/run_local_sync.py                 # 拉取→采集→审核→合并→校验/测试→提交推送
python scripts/run_local_sync.py --skip tianchi  # 跳过某些源
python scripts/run_local_sync.py --no-push       # 只提交不推送
```

天池等国内/反爬源建议用它在**本机**跑（国内 IP + 真实浏览器更易通过）；国际 API 源（Devpost/MLH/Kaggle）也可交给 GitHub Actions 的每周工作流。配合 Windows 任务计划程序调用 `run_local_sync.py` 即可每周自动运行。

GitHub 周更（对齐 X-daily）：周一 **10:17** 主跑 + **22:47** 备用（北京时间，非整点）；成功后写 `data/sync_state.json`，同周备用槽跳过。手动 Run workflow 始终会跑。

## 入口清单

```bash
python scripts/list_portals.py
```

清单直接读取 `sources.yaml`，不再维护 Python 内置副本。

## 数据和链接检查

```bash
python scripts/validate_data.py
python scripts/check_links.py
```

链接巡检区分正常、重定向、疑似反爬、证书错误、超时、网络错误和明确失效。证书或超时默认只进入报告，404/410 会使命令失败。

## 重要边界

- 采集器不自动写入 `data/competitions.json`。
- `needs_review=true` 的记录不能保留公开赛程字段。
- 赛事深链接和品牌首页分开保存。
- `migrate_schema_v3.py` 是一次性历史迁移脚本，schema 已为 v3 时会拒绝再次运行。

