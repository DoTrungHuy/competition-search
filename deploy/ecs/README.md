# 阿里云 ECS 迁移与运维指南

本目录提供将 `competition-search` 迁移至 **阿里云 ECS 实例** 的全套生产配置。你可以根据需求选择：

1. **后端容器化部署（API + MariaDB + 自动备份）**：与仓库根目录的 `docker-compose.yml` + `docker-compose.prod.yml` 及 [`deploy/PRODUCTION.md`](../PRODUCTION.md) 配合，将当前运行在本机 Cloudflare Tunnel 后的 `api.cs-contest.cn` 迁至阿里云 ECS。
2. **前端静态站 + 本机周更采集一体化托管**：将前端 `njupt.cs-contest.cn`、天池 Playwright + 南邮校内通知采集（`systemd` 定时器）以及 SQLite 页面浏览计数服务一并迁至阿里云 ECS，彻底脱离个人电脑 Windows 计划任务。

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

### 3. 启用 ECS 本机自动周更（替代个人电脑 Windows 计划任务）

在阿里云国内 ECS 上可直接访问南邮创学院通知网与阿里云天池：

```bash
cd /opt/competition-search
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements-scripts.txt -r requirements-playwright.txt
.venv/bin/playwright install --with-deps chromium

sudo tee /etc/competition-search.env >/dev/null <<'EOF'
DEEPSEEK_API_KEY=在此填入你的密钥
EOF
sudo chmod 600 /etc/competition-search.env

sudo cp /opt/competition-search/deploy/ecs/competition-sync.service /etc/systemd/system/
sudo cp /opt/competition-search/deploy/ecs/competition-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now competition-sync.timer
```

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
