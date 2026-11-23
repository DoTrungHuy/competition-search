# Competition Search · 南邮竞赛信息平台

<p align="center">
  <img src="assets/images/njupt-badge.png" alt="南京邮电大学校徽" width="88" />
</p>

<p align="center">
  面向南京邮电大学学生的竞赛信息聚合、检索与审核平台。<br/>
  从外部数据采集、AI 辅助审核、人工复核，到 Spring Boot API、MariaDB 持久化与前端展示，形成完整的数据闭环。
</p>

<p align="center">
  <a href="https://njupt.cs-contest.cn"><img src="https://img.shields.io/badge/Live-njupt.cs--contest.cn-7c5cff?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Live site" /></a>
  &nbsp;
  <a href="https://github.com/DoTrungHuy/competition-search/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/DoTrungHuy/competition-search/ci.yml?branch=main&style=for-the-badge&label=CI" alt="CI" /></a>
  &nbsp;
  <a href="https://github.com/DoTrungHuy/competition-search/actions/workflows/weekly-sync.yml"><img src="https://img.shields.io/github/actions/workflow/status/DoTrungHuy/competition-search/weekly-sync.yml?branch=main&style=for-the-badge&label=Weekly%20Sync" alt="Weekly Sync" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Java-21-ED8B00?style=flat-square&logo=openjdk&logoColor=white" alt="Java 21" />
  <img src="https://img.shields.io/badge/Spring%20Boot-4.1-6DB33F?style=flat-square&logo=springboot&logoColor=white" alt="Spring Boot" />
  <img src="https://img.shields.io/badge/MariaDB-11-003545?style=flat-square&logo=mariadb&logoColor=white" alt="MariaDB" />
  <img src="https://img.shields.io/badge/Python-Data%20Pipeline-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/DeepSeek-AI%20Review-4D6BFE?style=flat-square" alt="DeepSeek" />
</p>

**在线站点：<https://njupt.cs-contest.cn>**

> 本项目不是学校官方报名系统。报名、组队、奖项认定与赛事规则请以赛事官网和学校正式通知为准。

---

## 项目简介

这是一个面向南京邮电大学学生的竞赛数据平台，提供竞赛检索、自动采集、AI 辅助审核和人工复核。

系统定期从校园通知、Devpost、MLH、Kaggle、天池等来源采集候选赛事。DeepSeek 给出审核建议；`ACCEPT` 且置信度为 `HIGH` 或 `MEDIUM` 的候选会自动写入正式竞赛数据，其余候选由管理员在后台处理。正式数据保存在 MariaDB 中，由 Spring Boot REST API 提供给前端展示。

### 首页预览

<p align="center">
  <img src="assets/images/readme/home.png" alt="竞赛查询首页截图" width="920" />
</p>

---

## 核心架构

```mermaid
flowchart TD
    A[校园通知 / Devpost / MLH / Kaggle] --> B[Python Collectors]
    B --> C[review_queue.json]
    C --> D[DeepSeek Flash]
    D --> E[AI 建议<br/>verdict / confidence / reason]
    E --> F[(review_candidates)]
    F --> G[Spring Security 管理后台]
    G -->|人工通过| H[(competitions)]
    G -->|人工拒绝| I[REJECTED]
    H --> J[Spring Boot REST API]
    J --> K[前端竞赛查询站]

    L[GitHub Actions] --> B
    L --> M[测试 / 数据校验 / E2E]
    L --> N[内部同步 API]
    N --> F
    N --> H
```

整个系统的原则是：

```text
人工审核
   >
AI 建议
   >
自动采集
```

AI 不会直接替代管理员做最终数据决策。

---

## 功能亮点

### 用户侧

- 按名称、品牌、标签搜索竞赛
- 按全国赛 / 大厂赛 / 国际赛等类型筛选
- 展示报名中、即将报名、即将开始、进行中等状态
- 支持学校竞赛认定档位、赛程和参赛要求摘要
- 跳转赛事官网或已核验原始通知
- API 异常时保留静态数据兜底能力

### 管理与数据治理

- Python 自动采集多个数据源
- DeepSeek 对候选赛事给出 `ai_verdict / ai_confidence / ai_reason`
- `ACCEPT` 且置信度为 `HIGH` 或 `MEDIUM` 的候选由脚本自动写入正式竞赛数据
- 无法匹配品牌、`REJECT`、`LOW` 或尚未审核的候选保留为 `PENDING`
- Spring Security 管理员登录
- 单条审核、编辑后通过、拒绝
- 全选 / 批量批准 / 一键批准 HIGH 置信度候选
- 人工审核结果优先，后续自动同步不会覆盖人工决定
- 内容指纹避免同一候选重复调用 AI

### 工程化

- Spring Boot 分层架构：Controller / Service / Repository
- Spring Data JPA + Hibernate ORM
- MariaDB 持久化
- Flyway 数据库版本迁移
- Session + CSRF + 角色权限控制
- GitHub Actions CI
- Python / JavaScript / Java 自动测试
- Playwright E2E 浏览器冒烟测试
- Weekly Sync 自动采集与数据同步
- 阿里云 ECS 运行网站、API、数据库和备份

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | HTML / CSS / Vanilla JavaScript |
| 后端 | Java 21 / Spring Boot 4.1 / Spring MVC |
| 数据访问 | Spring Data JPA / Hibernate |
| 数据库 | MariaDB |
| 数据库迁移 | Flyway |
| 安全 | Spring Security / Session / CSRF |
| 数据采集 | Python / Requests / Playwright |
| AI 审核 | DeepSeek API |
| 自动化 | GitHub Actions |
| 测试 | JUnit / H2 / Node Test / Python unittest / Playwright |
| 部署 | 阿里云 ECS / Docker Compose / Nginx / Cloudflare |

---

## 后端设计

### 分层结构

```text
Controller
    ↓
Service
    ↓
Repository
    ↓
MariaDB
```

主要业务模块：

```text
backend/src/main/java/cn/trunghuy/competition/
├── controller/
│   ├── CompetitionController.java
│   ├── AdminReviewController.java
│   ├── AdminSessionController.java
│   └── InternalSyncController.java
├── service/
│   ├── CompetitionService.java
│   ├── CompetitionSyncService.java
│   ├── ReviewCandidateSyncService.java
│   └── AdminReviewService.java
├── repository/
│   ├── CompetitionRepository.java
│   └── ReviewCandidateRepository.java
├── entity/
│   ├── Competition.java
│   └── ReviewCandidate.java
└── config/
    └── SecurityConfig.java
```

### 数据模型

当前主要有两类业务数据：

```text
review_candidates
    ↓ 人工审核
competitions
```

`review_candidates` 保存待审核候选、AI 建议、人工审核状态与原始 JSON；`competitions` 是正式对外提供的数据。

审核状态：

```text
PENDING
  ├──→ APPROVED → competitions
  └──→ REJECTED
```

### Flyway

数据库结构不依赖 Hibernate 自动改表，而由 Flyway 管理：

```text
V1__create_competition_tables.sql
V2__create_review_candidates.sql
V3__add_review_decision_fields.sql
```

生产环境使用：

```properties
spring.jpa.hibernate.ddl-auto=validate
```

避免应用启动时静默修改数据库结构。

---

## API

### 公开接口

```http
GET /api/competitions
GET /api/hello
```

### 管理员接口

需要 Spring Security 登录 Session：

```http
GET  /api/admin/reviews
GET  /api/admin/reviews/{id}
POST /api/admin/reviews/{id}/approve
POST /api/admin/reviews/{id}/reject
POST /api/admin/reviews/bulk/approve
```

后台写操作同时启用 CSRF 防护。

### 内部同步接口

供 GitHub Actions / 数据管线调用：

```http
POST /api/internal/sync
POST /api/internal/review-candidates/sync
```

通过独立的 `X-Sync-Token` 认证，不与管理员 Session 混用。

---

## 数据采集与 AI 审核

自动管线：

```text
fetch_*.py
    ↓
draft_*.json
    ↓
review_drafts.py
    ↓
DeepSeek AI 建议
    ↓
review_queue.json
    ↓
内部同步 API
    ↓
review_candidates
    ↓
管理员人工审核
```

当前设计中 DeepSeek **不会自动批准或拒绝**候选，只写入辅助判断：

```text
ai_verdict
ai_confidence
ai_reason
```

候选内容未发生变化时，会复用已有 AI 结果，避免重复消耗 API。

---

## Weekly Sync

GitHub Actions 每周自动执行：

```text
采集多个数据源
      ↓
汇总采集健康状态
      ↓
DeepSeek 生成审核建议
      ↓
刷新固定清单预计报名
      ↓
数据校验
      ↓
JS / Python 测试
      ↓
提交数据变化
      ↓
同步 MariaDB
      ↓
外链健康巡检
```

特点：

- 双 cron 时间槽，降低 GitHub Actions 定时漏跑影响
- 本周已成功执行时备用槽自动跳过
- 单个采集源失败可容忍
- 所有实际数据源都失败时整轮失败
- AI 可通过变量独立开关
- 数据校验或测试失败时不会提交生产数据

---

## 项目目录

```text
competition-search/
├── backend/                    # Spring Boot 后端
│   ├── src/main/java/          # Controller / Service / Repository / Entity
│   └── src/main/resources/
│       ├── db/migration/       # Flyway SQL
│       └── static/admin/       # 管理员审核后台
├── data/
│   ├── competitions.json       # 静态生产数据 / 版本记录
│   ├── review_queue.json       # AI 辅助审核队列
│   ├── brands.json
│   └── sync_state.json
├── scripts/                    # Python 数据采集与校验
├── js/                         # 前端交互逻辑
├── css/                        # 前端样式
├── tests/
│   ├── js/
│   ├── python/
│   └── e2e/
├── .github/workflows/
│   ├── ci.yml
│   └── weekly-sync.yml
├── index.html
└── about.html
```

---

## 本地开发

### 1. 前端

```bash
npm run serve
```

浏览器打开 `http://localhost:4173`。

### 2. Python 数据脚本

```bash
python -m pip install -r requirements-scripts.txt
```

常用命令：

```bash
python scripts/validate_data.py
python scripts/check_links.py
```

### 3. Spring Boot

需要：

- Java 21
- MariaDB

复制环境变量模板：

```bash
cp backend/.env.example backend/.env.local
```

主要环境变量：

```text
DB_URL
DB_USERNAME
DB_PASSWORD
SYNC_TOKEN
ADMIN_USERNAME
ADMIN_PASSWORD
SESSION_COOKIE_SECURE
```

构建并启动：

```bash
cd backend
./mvnw -DskipTests package
./scripts/start-backend.sh
```

`start-backend.sh` 会读取 `backend/.env.local`，并在需要时尝试启动本机 MariaDB。默认监听 `127.0.0.1:8080`。

停止后端：

```bash
./scripts/stop-backend.sh
```

> `.env.local`、API Key、数据库密码和 Token 不应提交到 Git。

---

## 测试

### 前端 / Python / 数据校验

```bash
npm test
```

包括：

- JavaScript 语法检查
- JavaScript 单元测试
- Python 单元测试
- 生产数据校验

### Spring Boot

```bash
cd backend
./mvnw test
```

覆盖：

- Flyway migration
- Repository / Service
- Competition sync
- Review candidate sync
- 人工审核流程
- 批量审核
- Spring Security
- Session / CSRF
- 内部同步接口

### E2E

```bash
python -m pip install -r requirements-playwright.txt
python -m playwright install chromium
npm run test:e2e
```

CI 中 E2E 与普通测试并行运行。

---

## 安全设计

- 数据库只由 Spring Boot 访问，不直接暴露给公网
- 管理后台使用 Spring Security Session
- 后台写操作启用 CSRF
- Session Cookie 设置 `Secure / HttpOnly / SameSite=Lax`
- GitHub Actions 使用独立同步 Token
- API Key、数据库密码、管理员密码放在环境变量 / GitHub Secrets
- DeepSeek 可以自动发布高置信度和中置信度的 `ACCEPT` 候选；人工已通过或已拒绝的记录不会被后续同步覆盖

---

## 部署

### Docker Compose（本机验证 / ECS 生产）

生产环境运行在阿里云 ECS 上。ECS 前面由统一网关按域名转发，仓库内的 Docker Compose 同时运行网站、API、数据库和备份：

```text
Cloudflare
    ↓
ECS 统一网关
    ↓
Docker Nginx
    ├── 网站、CSS、JavaScript、JSON
    └── /api、/admin → Spring Boot → MariaDB
```

`njupt.cs-contest.cn` 和 `cs-contest.cn` 由 Nginx 返回静态网站；`api.cs-contest.cn` 的请求转给 Spring Boot。数据库端口不向公网开放。

仓库根目录已提供 `docker-compose.yml`、`docker.env.example`、`backend/Dockerfile` 和 `deploy/nginx/api.conf`。

首次启动：

```bash
cp docker.env.example .env
# 编辑 .env，替换所有 replace_with_* 密码 / Token
docker compose up -d --build
```

默认本机入口：

```text
http://127.0.0.1:8088/api/competitions
http://127.0.0.1:8088/admin/
http://127.0.0.1:8088/actuator/health
```

`/actuator/health` 是公开健康检查端点，其余 Actuator 端点不对外暴露。
Docker 使用该端点判断 Spring Boot 是否真正可用；Nginx 会等待后端进入 `healthy` 状态后再启动。

MariaDB 数据放在 named volume `mariadb_data` 中，重新构建后端镜像不会删除数据库。
只有明确需要连数据库一起清空时，才执行 `docker compose down -v`。

### 数据库备份与恢复

生产 Compose 额外启动 `db-backup` 容器。默认启动后立即备份一次，之后每 24 小时备份一次，并保留 14 天。
备份文件写入仓库根目录下的 `backups/`，该目录不会提交到 Git。

可在 `.env` 中调整：

```text
BACKUP_INTERVAL_SECONDS=86400
BACKUP_RETENTION_DAYS=14
```

需要立刻手工备份时：

```bash
bash deploy/backup/backup-now.sh
```

恢复数据库前建议先再做一次当前状态备份。恢复命令要求显式确认：

```bash
bash deploy/backup/restore-db.sh backups/competition_search-YYYYMMDDTHHMMSSZ.sql.gz --confirm
```

如果 `backups/` 与数据库仍位于同一台服务器，它只能防止误删和容器损坏，不能防止整台服务器或磁盘损坏。
正式上线后应再把备份同步到 OSS 等独立存储。

ECS 上使用服务器自己的 `.env`，真实 `.env` 不提交到 GitHub。

### 生产 Compose 与 HTTPS

生产环境使用基础 Compose 与生产覆盖文件：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

生产覆盖会：

- 将 Session Cookie 强制设为 Secure
- 限制 MariaDB、Spring Boot、Nginx 和备份容器的内存
- 使用阿里云 Maven 镜像构建后端
- 使用 `deploy/nginx/api.conf`，由 ECS 前面的统一网关处理 HTTPS
- 启动自动数据库备份容器
- 在同一台 ECS 上发布网站文件和 API

因此生产 Compose 不在容器内重复监听公网 443，也不使用独立的 `api.prod.conf`。Cloudflare 作为域名和 HTTPS 代理，SSL/TLS 模式使用 **Full (strict)**。

### GitHub Actions 自动部署

仓库包含 `.github/workflows/deploy.yml`。自动部署默认关闭；正式服务器准备好后，
将 Repository Variable `PRODUCTION_DEPLOY_ENABLED` 设为 `true` 才会启用；SSH 私钥等敏感信息保存在 `production` Environment Secrets。

启用后，`main` 的 CI 全部成功才会部署对应的**精确 commit SHA**，而不是在服务器上盲目 `git pull`。
发布过程会在更新前备份数据库，更新后检查容器健康、Nginx 配置和公网 HTTPS 健康状态。
若应用发布失败，会尝试将应用代码自动回退到上一版本；数据库不会自动回退。

服务器首次准备、GitHub Variables / Secrets 和 SSH host key 配置详见 `deploy/PRODUCTION.md`。

### 当前线上形态

网站、API、MariaDB 和数据库备份运行在阿里云 ECS 上：

```text
njupt.cs-contest.cn / cs-contest.cn / api.cs-contest.cn
    ↓
Cloudflare
    ↓
阿里云 ECS
    ├── Docker Nginx：网站与反向代理
    ├── Spring Boot：竞赛 API、管理后台、内部同步
    ├── MariaDB：正式竞赛与审核队列
    └── db-backup：每天备份并保留 14 天
```

公网主域名 `njupt.cs-contest.cn` 的网页请求由 Cloudflare Worker 转发到 ECS 上的 Nginx。Worker 通过现有 `api.cs-contest.cn` HTTPS 通道读取源站的 `/_ecs_frontend/` 静态资源。

每周采集由 GitHub Actions 的 Weekly competition sync 调度，校验通过后经内部 API 同步至生产 MariaDB。生产服务器停用 ECS 采集定时器，使发布工作目录只由部署流程更新。静态备用数据随发布更新。

代码发布由 GitHub Actions 在 CI 成功后通过 SSH 把经过测试的 commit 推到 ECS。发布失败只回滚应用，不自动回滚数据库。`backend/scripts/start-tunnel.sh` 是迁移前的本机 Cloudflare Tunnel 脚本，不再是当前线上入口。

---

## Roadmap

当前重点不是继续堆业务功能，而是补生产部署能力：

- [x] Docker + Docker Compose 配置
- [x] 阿里云 ECS 线上部署
- [x] Nginx 反向代理；HTTPS 由 ECS 统一网关和 Cloudflare 处理
- [x] Spring Boot Actuator 健康检查
- [x] GitHub Actions 自动部署 / 应用失败回滚配置
- [x] MariaDB 自动备份 / 手工恢复
- [ ] API 分页与查询优化

Redis、MQ、微服务、Kubernetes 暂不引入：当前业务规模没有真实需求。

---

## 项目价值

这个项目重点不在“用了多少框架”，而在于完成了一条真实的数据闭环：

```text
数据采集
  ↓
AI 辅助判断
  ↓
人工数据治理
  ↓
关系型数据库
  ↓
REST API
  ↓
前端展示
  ↓
CI / 自动同步 / 线上部署
```

对于后端实践，项目覆盖了 Java Web 开发、数据库设计、权限控制、事务、数据迁移、自动测试、CI/CD 和线上部署等完整环节。

---

## 声明

数据与链接可能存在滞后或遗漏。

**报名、组队、赛程、奖项及学校认定请始终以赛事官网与学校正式通知为准。**

本项目为个人学习与信息查询辅助工具，不代表南京邮电大学官方教务部门、竞赛组织方或任何赛事主办方。
