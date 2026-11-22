# minecraft-server

A Minecraft server on AWS ECS Fargate with a Lambda-based Discord bot for
remote server management, in its own AWS account.

## 🎮 Features

- **Serverless Minecraft Server**: Runs on AWS ECS Fargate, off by default
- **Discord Bot Integration**: Start, stop, and check server status via
  Discord slash commands, handled by a Lambda behind Discord's
  Interactions webhook (no standing bot process, no static IAM credential)
- **Dynamic DNS**: Automatic IP updates via Cloudflare DNS
- **Idle Monitoring**: Automatic server shutdown when no players are online
- **Persistent Storage**: EFS-backed world data that persists across restarts
- **Cost Optimized**: Pay only when the server is running (Fargate Spot,
  `desired_count = 0` by default)

## 🏗️ Architecture

```
┌──────────────┐   HTTPS    ┌───────────────────┐   ECS API   ┌─────────────────┐
│   Discord     │──────────▶│  Lambda            │────────────▶│   ECS Service   │
│   (slash cmd) │           │  (discord_bot)      │             │   (Fargate)     │
└──────────────┘            └───────────────────┘             └─────────────────┘
                                                                        │
                                                        ┌───────────────┼────────────────┐
                                                        ▼               ▼                ▼
                                                 Minecraft task   mc-idle-watcher   ecs-dns-updater
                                                 (EFS-backed)     (auto-shutdown)   (Cloudflare DNS)
```

Everything lives in its own AWS subaccount (`minecraft-server`), separate
from the management account.

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with a session for the `minecraft-server` account
- Terraform >= 1.0
- Cloudflare account with API token
- A Discord Application (bot token + public key + application ID)

### 1. Configure Secrets

```bash
cp terraform/secrets.yaml terraform/secrets.yaml   # start from the decrypted file if you have one
# edit terraform/secrets.yaml: discord.public_key, discord.application_id,
# discord.bot_token, discord.webhook_url, cloudflare token

make encrypt
```

### 2. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

This creates the VPC, ECS cluster/service/task definition, EFS filesystem,
SSM parameters, the Discord bot Lambda (with a placeholder handler), and
its Function URL.

### 3. Deploy the real Lambda code

The Terraform apply only wires up the Lambda infrastructure; `main`
pushes going forward deploy the real handler automatically via
`.github/workflows/mc-discord-bot-lambda.yml`. For a first manual deploy:

```bash
make deploy
```

### 4. Register Discord commands and the Interactions endpoint

One-time setup in the Discord Developer Portal:

1. Paste the `discord_bot_function_url` Terraform output into the
   application's **Interactions Endpoint URL**.
2. Register the slash commands (needs your bot token, run locally — not
   something to automate with AWS credentials):

```bash
curl -sS -X PUT \
  "https://discord.com/api/v10/applications/${DISCORD_APPLICATION_ID}/commands" \
  -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '[
    {"name": "mc-start", "description": "Start the Minecraft server"},
    {"name": "mc-stop", "description": "Stop the Minecraft server"},
    {"name": "mc-status", "description": "Check server status and IP addresses"},
    {"name": "mc-help", "description": "Show bot help"}
  ]'
```

### 5. Discord Commands

- `/mc-start` - Start the Minecraft server
- `/mc-stop` - Stop the Minecraft server
- `/mc-status` - Check current server status
- `/mc-help` - Show all available commands with descriptions

## 📁 Project Structure

```
minecraft-server/
├── terraform/             # ECS cluster, service, task def, EFS, VPC, DNS, IAM, Lambda
├── src/minecraft_tools/
│   ├── discord_bot/       # Lambda handler for Discord Interactions
│   └── idle_watcher/      # Sidecar: stops the server when idle
├── docker/                # idle-watcher.Dockerfile (only Docker image this repo builds)
├── tests/
├── Makefile                # decrypt/encrypt, package/deploy, start/stop/restart, exec
└── .github/workflows/
```

DNS updates use `ghcr.io/melvyndekort/ecs-dns-updater`, a shared sidecar
image maintained in its own repo, not built here.

## ⚙️ Configuration

### Discord bot Lambda environment (set via Terraform secrets)

| Variable | Description |
|----------|-------------|
| `DISCORD_PUBLIC_KEY` | Used to verify Discord's Ed25519 request signatures |
| `DISCORD_APPLICATION_ID` | Discord application ID |
| `DISCORD_CHANNEL_ID` | Restrict commands to this channel (optional) |
| `ECS_CLUSTER` / `ECS_SERVICE` | Wired automatically to the real Terraform resources |

### Terraform Variables

Key variables in `terraform/terraform.tfvars`:

```hcl
region        = "eu-west-1"
dns_zone      = "dekort.dev"
dns_record    = "mc"
paper_version = "26.2"
task_cpu      = 2048
task_memory   = 4096
desired_count = 0  # Start with server stopped
```

## 🔒 Security

- No standing Discord bot process, no static IAM access key — the Lambda
  is invoked directly by Discord and verifies each request's Ed25519
  signature before doing anything
- EFS encryption at rest and in transit
- Security groups restrict access to the Minecraft/Geyser ports only
- Secrets managed via AWS SSM Parameter Store / KMS-encrypted Terraform secrets

## 💰 Cost Optimization

- Server runs only when needed (`desired_count = 0` by default)
- Fargate Spot pricing
- CloudWatch logs with 7-day retention
- Lambda bot only runs (and costs anything) when invoked

## 🔧 Container Access

To access the running Minecraft container for troubleshooting or configuration:

```bash
make exec
```

This opens an interactive shell in the Minecraft container. The server must be running first.

## 🎮 Server Management

You can manage the Minecraft server directly via command line, as an
alternative to the Discord bot:

```bash
make start
make stop
make restart   # force new deployment
```

## 🛠️ Development

```bash
make test
make lint
make format
make type-check
make dev-all     # all of the above
```

### Infrastructure Changes

```bash
cd terraform
terraform plan
terraform apply
```

## 📊 Monitoring

- CloudWatch logs: `/ecs/minecraft` and `/aws/lambda/minecraft-discord-bot`
- ECS service metrics available in AWS Console

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

**Discord bot not responding / "interactions endpoint could not be verified":**
- Check `/aws/lambda/minecraft-discord-bot` CloudWatch logs for import or
  runtime errors
- Confirm `make deploy` actually ran (check the Lambda's `LastModified`) —
  Terraform's apply only deploys a placeholder handler

**Server won't start:**
- Verify the ECS service exists and has a healthy task definition
- Check IAM permissions on `ecsTaskExecutionRole-mc`
- Review `/ecs/minecraft` task logs

**DNS not updating:**
- Verify the Cloudflare API token in SSM
- Check `ecs-dns-updater` sidecar logs in `/ecs/minecraft`
