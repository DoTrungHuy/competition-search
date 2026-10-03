# Production deployment

This project keeps application code in Git and machine-specific state on the production server.

## 1. One-time server preparation

Use a long-running Linux server with a public IP. Install Git, Docker Engine and Docker Compose v2, then clone the repository:

```bash
sudo mkdir -p /opt/competition-search
sudo chown "$USER":"$USER" /opt/competition-search
git clone https://github.com/DoTrungHuy/competition-search.git /opt/competition-search
cd /opt/competition-search
```

Create the production environment file:

```bash
cp docker.env.example .env
chmod 600 .env
```

Replace every placeholder password/token in `.env` with a unique random value.

Create a Cloudflare Origin Certificate for `api.cs-contest.cn` and place:

```text
deploy/certs/origin.pem
deploy/certs/origin.key
```

Protect the private key:

```bash
chmod 600 deploy/certs/origin.key
```

Run the first deployment manually:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Only SSH, HTTP and HTTPS should be exposed through the server firewall/security group. Do not publish MariaDB 3306 or Spring Boot 8080 directly.

## 2. GitHub deployment configuration

Configure these **Repository Variables**:

```text
PRODUCTION_DEPLOY_ENABLED=false
PRODUCTION_HOST=<server IP or DNS name>
PRODUCTION_USER=<SSH user>
PRODUCTION_SSH_PORT=22
PRODUCTION_APP_DIR=/opt/competition-search
```

Keep `PRODUCTION_DEPLOY_ENABLED=false` until the first manual deployment is healthy. Set it to `true` only when automatic deployment is ready.
Before enabling it, update Cloudflare so `api.cs-contest.cn` reaches the new server and verify HTTPS manually.

Then create a GitHub Environment named `production` and add these **Environment Secrets**:

```text
PRODUCTION_SSH_KEY=<private SSH deployment key>
PRODUCTION_SSH_KNOWN_HOSTS=<verified known_hosts line for the server>
```

The enable switch is intentionally a Repository Variable because the workflow evaluates it before assigning a runner to the `production` environment. Sensitive SSH material remains protected as Environment Secrets.

Do not use `ssh-keyscan` inside the deployment workflow as the trust decision. Verify the host key out of band, then save that pinned line in `PRODUCTION_SSH_KNOWN_HOSTS`.

Application secrets such as database passwords, admin password and sync token remain in the server-side `.env`; they are not copied through GitHub on each deployment.

## 3. Automatic release flow

After deployment is enabled, a push to `main` follows:

```text
push main
  -> CI
     -> JS / Python / Java tests
     -> E2E
     -> Docker builds
  -> Deploy production (only if CI succeeded)
     -> SSH with pinned host key
     -> pre-deploy MariaDB backup
     -> checkout exact CI-tested commit SHA
     -> docker compose up -d --build
     -> wait for backend healthy
     -> nginx -t
     -> local HTTPS health check
     -> public Cloudflare HTTPS health check
```

A deployment concurrency lock prevents two production releases from running at the same time.

## 4. Failure behavior

If the remote build/start/health check fails, `deploy/remote-deploy.sh` checks application code back out to the previous commit and attempts to rebuild the previous application stack.

Database state is deliberately **not** rolled back automatically. A pre-deploy SQL backup is created when the database is already running. If a schema migration needs recovery, inspect the failure first and restore a selected backup explicitly.

## 5. Manual deployment

The workflow also supports `workflow_dispatch`, but only from `main`. The production enable switch, SSH verification and health checks still apply.
