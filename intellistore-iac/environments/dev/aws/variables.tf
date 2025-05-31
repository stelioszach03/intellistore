variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "intellistore"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "private_subnets" {
  description = "List of private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "List of public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.27"
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "List of CIDR blocks that can access the Amazon EKS public API server endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_group_capacity_type" {
  description = "Type of capacity associated with the EKS Node Group"
  type        = string
  default     = "ON_DEMAND"
}

variable "node_group_instance_types" {
  description = "List of instance types associated with the EKS Node Group"
  type        = list(string)
  default     = ["m5.large", "m5.xlarge"]
}

variable "node_group_desired_size" {
  description = "Desired number of nodes in the EKS Node Group"
  type        = number
  default     = 3
}

variable "node_group_max_size" {
  description = "Maximum number of nodes in the EKS Node Group"
  type        = number
  default     = 10
}

variable "node_group_min_size" {
  description = "Minimum number of nodes in the EKS Node Group"
  type        = number
  default     = 1
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "intellistore.dev"
}

variable "create_route53_zone" {
  description = "Whether to create Route53 hosted zone"
  type        = bool
  default     = false
}

variable "create_acm_certificate" {
  description = "Whether to create ACM certificate"
  type        = bool
  default     = false
}