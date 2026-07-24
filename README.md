# 竞赛查询

面向南邮学生的竞赛搜索与筛选工具。首页优先展示当前仍可行动的机会，已结束赛事随后排列；官网没有统一精确日期时仅提示「见官网详情」，不推定时间或额外添加状态标签。

「学校网站有相关通知」只表示校内发布过通知，不代表南京邮电大学是赛事主办方。报名、组队和赛程最终以赛事原文为准。

已核验且尚未开始的 `registration_start` 会显示为「即将开始报名」；不要用往届规律自动推算下届报名日，应写入新一届官方日期。

## 当前状态

- 静态 HTML、CSS、JavaScript，无前端构建步骤。
- 生产数据使用 schema v3，拆分赛事、品牌和平台入口。
- 约 44 条赛事/赛道中，多数已完成本轮官方核验，7 条保留在内部复核队列。
- 校内采集只生成审核草稿，不会自动覆盖生产数据。
- 本地 Git 已初始化，未配置远端、未部署。

## 本地预览

```bash
npm run serve
```

浏览器打开 <http://localhost:4173>。不要直接用 `file://` 打开，因为页面需要通过 `fetch` 加载 JSON。

## 安装脚本依赖

```bash
python -m pip install -r requirements-scripts.txt
```

## 验证

```bash
npm test
python scripts/check_links.py
```

`npm test` 包含 JavaScript 语法、状态排序、采集解析和生产数据校验。链接巡检会生成忽略提交的 `reports/link-check.json`。

## 数据与采集

```text
data/competitions.json  具体赛事或赛道
data/brands.json        品牌和官网根地址
data/portals.json       天池、Devpost 等平台入口
scripts/sources.yaml    采集与巡查入口的唯一配置
```

拉取南邮通知草稿：

```bash
python scripts/fetch_campus_cxcy.py
```

输出写入 `scripts/out/draft_campus.json`，按 `new / changed / duplicate / rejected` 分类，供审核后再决定是否并入生产数据。脚本不会自动写入 `data/competitions.json`。

## 自动化管线

每周由 GitHub Actions（`.github/workflows/weekly-sync.yml`）自动执行，也可手动触发：

```text
采集  fetch_campus_cxcy.py / fetch_devpost.py  -> scripts/out/draft_*.json
审核  review_drafts.py（DeepSeek）             -> scripts/out/reviewed.json
合并  apply_reviewed.py                        -> data/competitions.json (+ brands.json)
闸门  validate_data.py + npm test 通过后才自动提交
```

- 审核用 DeepSeek，需在仓库 Settings → Secrets 配置 `DEEPSEEK_API_KEY`。
- 自动合并的记录一律 `needs_review=true`：只显示「见官网详情」，不含推断日期，排在列表末尾。
- 数据校验或测试不通过则中断，绝不提交坏数据。

## 视觉来源

页面保留项目既有的 web_beauty 多风格组合：

- liquidGlass / liquidGlassAgency：玻璃基底、导航和字体层级。
- openDoor：筛选芯片和导航的流体交互。
- bloom：列表卡片的模糊层次。
- flower：轻量背景粒子。
- blueEyes：主标题层级。

字体文件已经本地化；页面不展示数据维护日期。
