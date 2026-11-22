# 阿里云 ECS 迁移与运维指南

当前生产环境已经运行在阿里云 ECS 上，不再使用个人电脑上的 Cloudflare Tunnel。本目录包含 ECS 上的采集、发布和计数配置：

1. **Docker Compose 生产栈**：`docker-compose.yml`、`docker-compose.prod.yml` 和 [`deploy/PRODUCTION.md`](../PRODUCTION.md) 在 ECS 上运行 Nginx、Spring Boot、MariaDB 与自动备份。
2. **每周采集**：GitHub Actions 采集和校验赛事，通过内部 API 写入 ECS 上的 MariaDB。
3. **可选的 SQLite 浏览计数**：需要把浏览计数从 API 域名切换到网站域名时，再启用本节的本机计数服务。

---

## 一、迁移前准备（阿里云控制台）

1. **ICP 备案**：若 ECS 位于中国内地地域（如华东 1 杭州 / 华东 2 上海），域名 `cs-contest.cn` 必须在阿里云完成 ICP 备案（或备案接入），否则 80/443 端口会被机房拦截。
2. **安全组规则**：入方向仅放行 `80/tcp`（HTTP）、`443/tcp`（HTTPS）和 `22/tcp`（SSH）；**严禁**对外网暴露 `3306`（MariaDB）或 `8080`（Spring Boot）。
3. **推荐系统镜像**：Ubuntu 22.04 / 24.04 LTS（若同时运行 Spring Boot + MariaDB + Chromium 抓取天池，建议 2C4G 或配置 2GB Swap）。

---

## 二、方案 A：后端 API 容器化迁移（`api.cs-contest.cn`）

完全复用仓库已有的 Docker Compose 生产编排（详见 [`../PRODUCTION.md`](../PRODUCTION.md)）：

```bash
# 1. 安装 Docker 与 Compose v2 并克隆仓库
sudo mkdir -p /opt/competition-search
sudo chown "$USER":"$USER" /opt/competition-search
git clone https://github.com/DoTrungHuy/competition-search.git /opt/competition-search
cd /opt/competition-search

# 2. 配置生产环境变量与 TLS 证书
cp docker.env.example .env
chmod 600 .env
# 编辑 .env 填入 DB_PASSWORD / DB_ROOT_PASSWORD / SYNC_TOKEN / ADMIN_PASSWORD
# 将证书放入 deploy/certs/origin.pem 与 deploy/certs/origin.key（chmod 600）

# 3. 启动生产容器栈（MariaDB + Spring Boot + Nginx + 每日自动备份）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

验证健康检查通过后，在 GitHub 仓库设置 `PRODUCTION_HOST`（ECS 公网 IP）、`PRODUCTION_SSH_KEY` 等，并将 `PRODUCTION_DEPLOY_ENABLED=true`，此后每次 `main` 分支通过 CI 即自动部署并支持失败自动回滚（见 [`../remote-deploy.sh`](../remote-deploy.sh)）。

---

## 三、方案 B：前端静态站 + 周更采集 + 本机计数迁至 ECS

### 1. 发布静态文件到 `/var/www/competition-search`

利用 `deploy/ecs/deploy_static.sh` 按 `.assetsignore` 过滤，确保 `backend/`、`scripts/`、`.git/`、`.env` 绝不进入公开 Web 目录：

```bash
sudo bash /opt/competition-search/deploy/ecs/deploy_static.sh
sudo chown -R www-data:www-data /var/www/competition-search
```

### 2. 配置宿主机或容器 Nginx（见 `deploy/ecs/nginx.conf`）

```bash
sudo cp /opt/competition-search/deploy/ecs/nginx.conf /etc/nginx/sites-available/competition-search
sudo ln -sf /opt/competition-search/deploy/ecs/nginx.conf /etc/nginx/sites-enabled/competition-search
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d njupt.cs-contest.cn -d cs-contest.cn
```

### 3. 生产数据同步

[Weekly competition sync](../../.github/workflows/weekly-sync.yml) 负责定时采集和校验，并通过内部 API 将结果写入 ECS 上的 MariaDB。生产服务器保留专用于部署的 Git 工作目录。曾安装 ECS 定时器的生产主机可按以下方式停用它：

```bash
sudo systemctl disable --now competition-sync.timer
```

需要独立运行 ECS 采集脚本时，请使用单独的可写 Git 克隆目录，预装 Node.js、npm 和 Python 采集依赖，并通过服务环境提供同步所需配置。

### 4. （可选）启用 ECS 本机 SQLite 浏览计数服务

国内网络访问 `api.counterapi.dev` 偶有超时。启用本机 SQLite 计数服务后响应耗时 < 5ms：

```bash
sudo mkdir -p /var/lib/competition-search
sudo chown -R www-data:www-data /var/lib/competition-search
sudo cp /opt/competition-search/deploy/ecs/competition-counter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now competition-counter.service
```

取消 `nginx.conf` 中 `location = /api/visits/up` 的注释并重载 Nginx，前端设置 `window.COMP_COUNTER_URL = "/api/visits/up"` 即可切换至同源计数。
