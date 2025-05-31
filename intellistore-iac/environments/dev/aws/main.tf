terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Configure your S3 backend here
    # bucket = "your-terraform-state-bucket"
    # key    = "intellistore/dev/terraform.tfstate"
    # region = "us-west-2"
    # dynamodb_table = "terraform-state-lock"
    # encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "intellistore"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  cluster_name = "${var.project_name}-${var.environment}"
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# VPC Module
module "vpc" {
  source = "../../../modules/aws/vpc"

  name = local.cluster_name
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway = true
  enable_vpn_gateway = false
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = local.tags
}

# EKS Module
module "eks" {
  source = "../../../modules/aws/eks"

  cluster_name                          = local.cluster_name
  kubernetes_version                    = var.kubernetes_version
  subnet_ids                           = module.vpc.public_subnets
  private_subnet_ids                   = module.vpc.private_subnets
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs

  node_group_capacity_type   = var.node_group_capacity_type
  node_group_instance_types  = var.node_group_instance_types
  node_group_desired_size    = var.node_group_desired_size
  node_group_max_size        = var.node_group_max_size
  node_group_min_size        = var.node_group_min_size

  tags = local.tags
}

# Storage Module
module "storage" {
  source = "../../../modules/aws/storage"

  cluster_name = local.cluster_name
  
  # SSD Storage Class
  ssd_storage_class_name = "gp3-ssd"
  ssd_volume_type        = "gp3"
  ssd_iops               = 3000
  ssd_throughput         = 125

  # HDD Storage Class
  hdd_storage_class_name = "sc-standard-hdd"
  hdd_volume_type        = "gp2"

  tags = local.tags
}

# Route53 Zone (optional)
resource "aws_route53_zone" "intellistore" {
  count = var.create_route53_zone ? 1 : 0
  name  = var.domain_name

  tags = local.tags
}

# ACM Certificate (optional)
resource "aws_acm_certificate" "intellistore" {
  count           = var.create_acm_certificate ? 1 : 0
  domain_name     = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = [
    "*.${var.domain_name}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = local.tags
}