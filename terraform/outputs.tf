output "discord_bot_function_url" {
  description = "Register this as the Discord Application's Interactions Endpoint URL"
  value       = aws_lambda_function_url.discord_bot.function_url
}

output "ecs_cluster_id" {
  value = aws_ecs_cluster.minecraft.id
}

output "ecs_service_name" {
  value = aws_ecs_service.minecraft.name
}

output "efs_id" {
  value = aws_efs_file_system.minecraft.id
}

output "dns_name" {
  value = local.fqdn
}
