# Production TLS certificates

This directory intentionally contains no real certificate or private key in Git.

For the current Cloudflare-based production setup, create a Cloudflare Origin Certificate for `api.cs-contest.cn` and place:

- certificate at `deploy/certs/origin.pem`
- private key at `deploy/certs/origin.key`

Keep Cloudflare SSL/TLS mode on **Full (strict)**.

The real certificate and key are ignored by Git. Never commit the private key.
