resource "aws_iam_role" "discord_bot_lambda" {
  name = "minecraft-discord-bot-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "discord_bot_lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.discord_bot_lambda.name
}

data "aws_iam_policy_document" "discord_bot_lambda_ecs" {
  statement {
    sid    = "ControlMinecraftService"
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:UpdateService",
      "ecs:DescribeTasks",
      "ecs:ListTasks",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "ResolveTaskPublicIps"
    effect    = "Allow"
    actions   = ["ec2:DescribeNetworkInterfaces"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "discord_bot_lambda_ecs" {
  name   = "minecraft-discord-bot-ecs"
  role   = aws_iam_role.discord_bot_lambda.id
  policy = data.aws_iam_policy_document.discord_bot_lambda_ecs.json
}

resource "aws_iam_role_policy" "discord_bot_lambda_self_invoke" {
  name = "self-invoke"
  role = aws_iam_role.discord_bot_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.discord_bot.arn
      }
    ]
  })
}
