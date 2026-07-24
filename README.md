# 竞赛查询（南邮 · 计算机相关）

面向 **南京邮电大学学生** 的竞赛信息查询站：快速查找还能报名、即将开报、正在进行或即将开赛的比赛，并跳到官网或品牌入口核对原文。

**线上地址：<https://njupt.cs-contest.cn>**

---

## 给谁用

| 对象 | 能帮什么 |
|------|----------|
| 南邮在校生（尤其计软网安等） | 按关键词/类型筛竞赛，看时间与参赛要求摘要 |
| 想冲校认定目录的同学 | 标有「校认定 A/B/C/C2」的条目来自学校创新创业竞赛认定目录中的计算机相关固定清单 |
| 辅导员/实验室同学 | 分享同一入口，减少到处翻通知 |

**不是**学校官方报名系统，也**不能**代替赛事官网与校内正式通知。

---

## 能做什么

- **搜索**：名称、品牌、标签等
- **筛选**：全部 / 全国赛 / 大厂赛 / 国际赛；以及 **报名中**、**即将开始报名**、**进行中** 等状态
- **卡片信息**：时间线、简要要求、状态角标；校认定档位；「预计」标记
- **外链**：有已核验原文 →「查看原文」；预计或仅品牌入口 →「赛事主页」
- **关于页**：状态与数据边界说明（`about.html`）

### 状态怎么理解（产品规则）

| 状态 | 含义 |
|------|------|
| **报名中** | 报名窗口开着（已核验官方日期，或固定清单上标了「预计」的推算窗口） |
| **即将开始报名** | 开报日在未来 **1～30 天**内（不含开报当天）；**国际赛不进**此筛选 |
| **即将开始** | 比赛尚未开始（常有比赛日、报名可能已结束或未录入） |
| **进行中** | 比赛日已到且未结束 |
| **预计** | 报名日据往年已核验窗口推算，**不是**官网通知；按钮只给品牌官网，不给假报名深链 |

其它约定：

- **「全部」主栏**默认是国内相关赛事；**国际赛**单独成类（黑客松等在报时，请点「国际赛」或搜索）。
- 「学校网站有相关通知」只说明校内发过通知，**不等于**学校主办。
- 待人工复核、无可靠赛程的条目不显示精确公开状态，多为「见官网详情」。
- 页面上的「刷新列表」只重新加载本站已保存的数据，**不会**当场去外网抓取。

---

## 在线使用

打开 **[https://njupt.cs-contest.cn](https://njupt.cs-contest.cn)** 即可，无需安装。

建议用手机或电脑现代浏览器；若刚更新后内容异常，可强制刷新（Ctrl+F5 / 清缓存）。

---

## 本地预览（开发/验收）

```bash
npm run serve
```

浏览器打开 <http://localhost:4173>。  
**不要**用 `file://` 打开，页面需要通过 HTTP 加载 JSON。

```bash
npm test                          # JS 语法 + 单元测试 + 生产数据校验
python scripts/validate_data.py   # 仅数据校验
python scripts/check_links.py     # 外链巡检（生成 reports/，不入库）
```

脚本依赖：

```bash
python -m pip install -r requirements-scripts.txt
```

---

## 项目如何实现（维护者）

技术形态：**纯静态站**（HTML / CSS / JS + `data/*.json`），无前端构建。  
线上通过 **Cloudflare Workers 静态资源** 发布根目录（见 `wrangler.toml`）；域名 **njupt.cs-contest.cn**。

### 目录要点

| 路径 | 作用 |
|------|------|
| `index.html` / `about.html` | 查询页 / 关于 |
| `js/status.js` | 报名/比赛状态、芯片契约、外链诚信解析 |
| `js/app.js` | 列表、筛选、抽屉 |
| `data/competitions.json` / `brands.json` / `portals.json` | 生产数据（schema v3） |
| `scripts/validate_data.py` | 数据闸门（含链接诚信） |
| `scripts/link_integrity.py` | 禁止预计假深链、`?estimate=` 等 |
| `scripts/apply_registration_estimates.py` | 固定清单「预计报名」维护 |
| `.github/workflows/ci.yml` | push/PR：`npm test` |
| `.github/workflows/weekly-sync.yml` | 周更：采集 → 审核 → 合并 → **刷新预计** → 校验 → 通过才提交 |

### 数据原则

1. **已核验**记录：需要 `last_checked`、可用赛程或官方状态；赛事深链不得与品牌首页简单重复，也不得带伪参数。  
2. **待复核**（`needs_review`）：不写公开精确报名/比赛日进状态计算。  
3. **预计报名**：仅 `njupt_fixed` 且存在往年已核验 `registration_*` 时生成；**不写** `link`（`link_kind: brand_home`）；前端只打开品牌 `official_home`。  
4. 官方 `registration_*` **优先于**预计字段。

手动刷新预计（一般不必，周更会跑）：

```bash
python scripts/apply_registration_estimates.py
# 复现可用：--today YYYY-MM-DD
```

### 自动化管线（周更）

```text
采集  fetch_*.py → draft_*.json
审核  review_drafts.py（DeepSeek；禁止臆造日期）
合并  apply_reviewed.py
预计  apply_registration_estimates.py   ← 固定清单维护
闸门  validate_data.py + npm test       ← 含链接诚信，失败不提交
状态  data/sync_state.json              ← 本周成功标记（备用 cron 防重跑）
```

- 定时：周一北京时间约 10:17 / 22:47（UTC `02:17` / `14:47`），双槽 + 本周成功守卫。  
- Secrets：`DEEPSEEK_API_KEY`（必填）；Kaggle 可选。  
- 天池等需国内网络的源：本机 `scripts/run_local_sync.py` / Windows 任务（同样会跑预计维护）。  
- `scripts/upgrade_pending.py` 为**手动**补审工具，不进自动周更。

### 发布

静态资源部署示例：

```bash
npx wrangler deploy
```

仅 `git push` 更新仓库**不等于**线上一定已刷新；改完前端或数据后需按你的 Cloudflare 流程发布，用户侧建议强刷。

### 视觉

多风格组合（liquidGlassAgency 玻璃底、openDoor 芯片、bloom 卡片、flower 粒子等）；字体本地 WOFF2，不请求 Google Fonts；左上角南邮校徽；页面不展示本站维护日期。

---

## 验证与诚信

- `npm test`：语法检查、状态/访问量单测、Python 单测、**生产数据校验**。  
- 预计卡片与任何 `estimate=` / 往届冒充本届深链会被 **生成脚本 + validate + 前端** 拦截。  
- 外链 HTTP 存活巡检：`python scripts/check_links.py`（默认不进 CI，避免外网抖动挡合并）。

---

## 许可与声明

数据与链接可能滞后或不完整；**报名、组队、奖项认定一律以赛事官网与学校通知为准**。  
本仓库为查询辅助工具，不代表南京邮电大学官方教务或竞赛组委会立场。
