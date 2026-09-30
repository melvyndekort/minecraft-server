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

This repo builds 2 Docker images from a shared Python monorepo:
- `mc-discord-bot` — Discord bot for server control (`src/minecraft_tools/discord_bot/`)
- `mc-idle-watcher` — Monitors player count, stops server when idle (`src/minecraft_tools/idle_watcher/`)

DNS updates use `ghcr.io/melvyndekort/ecs-dns-updater` — a third-party
(same-owner) generic sidecar, not built from this repo. It was extracted
from here (originally `mc-dns-updater`) into its own repo so hermes-agent
could reuse it instead of each repo maintaining its own DNS-update
mechanism. See `terraform/minecraft.tf` for how it's wired in.

Each of the 2 remaining components has its own Dockerfile in `docker/`,
its own workflow, and its own GHCR image. They share a reusable workflow
(`build-component.yml`) for test → build → multi-arch manifest.

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
- **Still in the management account.** Priority 1 subaccount migration
  candidate — see `~/.claude/references/subaccount-migration.md`.

## MCP servers

This repo has a project-scoped `cloudflare` MCP server (`.mcp.json`) — see `~/.claude/references/mcp-catalog.md`.

## Related Repositories

- `~/src/melvyndekort/ecs-dns-updater` — shared sidecar image used for
  Cloudflare DNS updates (extracted from this repo's old `mc-dns-updater`)
- `~/src/melvyndekort/tf-cloudflare` — DNS records for the Minecraft server
- `~/src/melvyndekort/tf-aws` — AWS account and networking
