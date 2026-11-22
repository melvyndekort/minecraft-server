# minecraft-server

> For global standards, way-of-workings, and pre-commit checklist, see `~/.claude/CLAUDE.md`

## Role

Python developer and AWS engineer.

## What This Does

Minecraft server on AWS ECS (Fargate) with three sidecar components:
Discord bot for remote management, `ecs-dns-updater` for dynamic IP
(shared image, see Related Repositories), and idle watcher for
auto-shutdown. Uses EFS for persistent world storage.

## Important: Multi-Component Repo

This repo builds 1 Docker image from a shared Python monorepo:
- `mc-idle-watcher` — Monitors player count, stops server when idle (`src/minecraft_tools/idle_watcher/`)

The Discord bot (`src/minecraft_tools/discord_bot/`) is NOT a Docker
image — it's a Lambda invoked directly by Discord's Interactions webhook,
deployed via `make package`/`make deploy` (see
`.github/workflows/mc-discord-bot-lambda.yml`).

DNS updates use `ghcr.io/melvyndekort/ecs-dns-updater` — a third-party
(same-owner) generic sidecar, not built from this repo. It was extracted
from here (originally `mc-dns-updater`) into its own repo so hermes-agent
could reuse it instead of each repo maintaining its own DNS-update
mechanism. See `terraform/minecraft.tf` for how it's wired in.

`mc-idle-watcher` has its own Dockerfile in `docker/`, its own workflow,
and its own GHCR image, using the reusable `build-component.yml` workflow
(test → build → multi-arch manifest).

## Repository Structure

- `src/minecraft_tools/` — Shared Python package: `discord_bot/` (Lambda),
  `idle_watcher/` (Docker sidecar)
- `tests/` — Test suite for all components
- `docker/` — `idle-watcher.Dockerfile` (the only component built as a container)
- `terraform/` — VPC, ECS cluster, service, task definition, EFS, DNS, IAM, Lambda
- `.github/workflows/build-component.yml` — Reusable workflow (test → build → manifest), used by `mc-idle-watcher.yml`
- `.github/workflows/mc-discord-bot-lambda.yml` — Test → package → deploy for the Discord bot Lambda
- `Makefile` — `test`, `coverage`, `lint`, `format`, `type-check`, `dev-all`, `start`, `stop`, `restart`, `exec`, `decrypt`, `encrypt`, `package`, `deploy`

## Linting

This repo uses `ruff` + `mypy` for type checking. Pylint should also be added for deep analysis for type checking, configured in `pyproject.toml`. Also has `.pre-commit-config.yaml`.

## Terraform Details

- Account: `minecraft-server` (`805751386945`), its own AWS subaccount —
  migrated out of the management account 2026-11-22
- Backend: S3 in `mdekort-tfstate-805751386945`
- Secrets: KMS context `target=tf-minecraft`

## MCP servers

This repo has a project-scoped `cloudflare` MCP server (`.mcp.json`) — see `~/.claude/references/mcp-catalog.md`.

## Related Repositories

- `~/src/melvyndekort/ecs-dns-updater` — shared sidecar image used for
  Cloudflare DNS updates (extracted from this repo's old `mc-dns-updater`)
- `~/src/melvyndekort/tf-cloudflare` — DNS records for the Minecraft server
- `~/src/melvyndekort/tf-aws` — AWS account and networking
