locals {
  azs = ["${var.region}a", "${var.region}b", "${var.region}c"]
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = "minecraft-server"
  cidr = "10.0.0.0/16"

  azs            = local.azs
  public_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]

  public_subnet_tags = {
    Tier = "Public"
  }

  create_igw = true

  enable_nat_gateway = false

  manage_default_security_group = true
  manage_default_route_table    = true
  manage_default_network_acl    = true

  enable_dns_hostnames    = true
  enable_dns_support      = true
  map_public_ip_on_launch = true

  enable_ipv6                                   = true
  public_subnet_assign_ipv6_address_on_creation = true
  public_subnet_ipv6_prefixes                   = [0, 1, 2]
  public_subnet_enable_dns64                    = false

  enable_flow_log = false
}
