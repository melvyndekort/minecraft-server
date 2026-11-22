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
