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

resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "ecsTaskExecutionRole-mc"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_ssm_access" {
  statement {
    effect = "Allow"

    actions = [
      "ssm:GetParameters",
      "ssm:GetParameter",
      "ssm:GetParametersByPath"
    ]

    resources = [
      aws_ssm_parameter.cloudflare_api_token.arn,
      aws_ssm_parameter.discord_webhook_url.arn
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "DescribeTasksForSidecars"
    effect = "Allow"
    actions = [
      "ecs:DescribeTasks",
      "ecs:ListTasks",
      "ec2:DescribeNetworkInterfaces"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ScaleOwnService"
    effect = "Allow"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices"
    ]
    resources = [aws_ecs_service.minecraft.arn]
  }

  statement {
    sid    = "EcsExec"
    effect = "Allow"
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ecs_ssm_access" {
  name   = "ecs-ssm-access"
  policy = data.aws_iam_policy_document.ecs_ssm_access.json
}

resource "aws_iam_role_policy_attachment" "ecs_ssm_access" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_ssm_access.arn
}
