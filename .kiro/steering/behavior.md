# minecraft-server

> For global standards, way-of-workings, and pre-commit checklist, see `~/.kiro/steering/behavior.md`

## Role

Python developer and AWS engineer.

## What This Does

Minecraft server on AWS ECS (Fargate) with three sidecar components: Discord bot for remote management, DNS updater for dynamic IP, and idle watcher for auto-shutdown. Uses EFS for persistent world storage.

## Important: Multi-Component Repo

This repo builds 3 separate Docker images from a shared Python monorepo:
- `mc-discord-bot` — Discord bot for server control (`src/minecraft_tools/discord_bot/`)
- `mc-dns-updater` — Updates Cloudflare DNS when server IP changes (`src/minecraft_tools/dns_updater/`)
- `mc-idle-watcher` — Monitors player count, stops server when idle (`src/minecraft_tools/idle_watcher/`)

Each has its own Dockerfile in `docker/`, its own workflow, and its own GHCR image. They share a reusable workflow (`build-component.yml`) for test → build → multi-arch manifest.

## Repository Structure

- `src/minecraft_tools/` — Shared Python package with 3 subpackages
- `tests/` — Test suite for all components
- `docker/` — Per-component Dockerfiles (`discord-bot.Dockerfile`, etc.)
- `terraform/` — ECS cluster, service, task definition, EFS, networking, DNS, IAM
- `.github/workflows/build-component.yml` — Reusable workflow (test → build → manifest)
- `.github/workflows/mc-*.yml` — Per-component triggers calling the reusable workflow
- `Makefile` — `test`, `coverage`, `lint`, `format`, `type-check`, `dev-all`, `start`, `stop`, `restart`, `exec`, `ssh`, `decrypt`, `encrypt`

## Linting

This repo uses `ruff` + `mypy` for type checking. Pylint should also be added for deep analysis for type checking, configured in `pyproject.toml`. Also has `.pre-commit-config.yaml`.

## Terraform Details

- Backend: S3 in `mdekort-tfstate-075673041815`
- Secrets: KMS context `target=tf-minecraft`

## Related Repositories

- `~/src/melvyndekort/tf-cloudflare` — DNS records for the Minecraft server
- `~/src/melvyndekort/tf-aws` — AWS account and networking
