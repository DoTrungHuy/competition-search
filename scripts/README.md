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

