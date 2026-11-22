output "discord_bot_function_url" {
  description = "Register this as the Discord Application's Interactions Endpoint URL"
  value       = aws_lambda_function_url.discord_bot.function_url
}
