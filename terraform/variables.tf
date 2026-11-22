variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "dns_zone" {
  description = "DNS zone where the DNS record will be created/updated (e.g. example.com)"
  type        = string
}

variable "dns_record" {
  description = "DNS record (e.g. mc.example.com)"
  type        = string
}

variable "discord_channel_id" {
  description = "Restrict Discord bot commands to this channel ID. Empty = no restriction."
  type        = string
  default     = ""
}

variable "task_cpu" {
  type    = number
  default = 1024
}

variable "task_memory" {
  type    = number
  default = 2048
}

variable "desired_count" {
  description = "Default desired count for the ECS service. Set 0 to keep it off by default."
  type        = number
  default     = 0
}

variable "paper_version" {
  description = "Minecraft Paper server version"
  type        = string
}
