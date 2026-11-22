data "archive_file" "discord_bot_placeholder" {
  type        = "zip"
  output_path = "discord-bot-lambda-placeholder.zip"

  source {
    filename = "handler.py"
    content  = <<EOF
def lambda_handler(event, context):
  raise NotImplementedError
EOF
  }
}

resource "aws_lambda_function" "discord_bot" {
  function_name = "minecraft-discord-bot"
  role          = aws_iam_role.discord_bot_lambda.arn
  handler       = "minecraft_tools.discord_bot.handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  # CI deploys real code via `aws lambda update-function-code` (see
  # .github/workflows/mc-discord-bot.yml), same pattern as aws-idc-pim.
  filename         = data.archive_file.discord_bot_placeholder.output_path
  source_code_hash = data.archive_file.discord_bot_placeholder.output_base64sha256

  environment {
    variables = {
      LOG_LEVEL              = "INFO"
      ECS_CLUSTER            = "minecraft-cluster"
      ECS_SERVICE            = "minecraft-service"
      DISCORD_PUBLIC_KEY     = try(local.secrets.discord.public_key, "")
      DISCORD_APPLICATION_ID = try(local.secrets.discord.application_id, "")
      DISCORD_CHANNEL_ID     = var.discord_channel_id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.discord_bot_lambda_basic,
    aws_iam_role_policy.discord_bot_lambda_ecs,
  ]

  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
    ]
  }
}

resource "aws_lambda_function_url" "discord_bot" {
  function_name      = aws_lambda_function.discord_bot.function_name
  authorization_type = "NONE" # Discord can't sign with IAM SigV4; signature verified in-app instead.
}
