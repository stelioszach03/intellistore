variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.27"
}

variable "subnet_ids" {
  description = "List of subnet IDs for the EKS cluster"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the EKS node groups"
  type        = list(string)
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "List of CIDR blocks that can access the Amazon EKS public API server endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_group_capacity_type" {
  description = "Type of capacity associated with the EKS Node Group. Valid values: ON_DEMAND, SPOT"
  type        = string
  default     = "ON_DEMAND"
}

variable "node_group_instance_types" {
  description = "List of instance types associated with the EKS Node Group"
  type        = list(string)
  default     = ["m5.large"]
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

variable "ebs_csi_driver_version" {
  description = "Version of the EBS CSI driver addon"
  type        = string
  default     = "v1.19.0-eksbuild.2"
}

variable "vpc_cni_version" {
  description = "Version of the VPC CNI addon"
  type        = string
  default     = "v1.13.2-eksbuild.1"
}

variable "coredns_version" {
  description = "Version of the CoreDNS addon"
  type        = string
  default     = "v1.10.1-eksbuild.1"
}

variable "kube_proxy_version" {
  description = "Version of the kube-proxy addon"
  type        = string
  default     = "v1.27.1-eksbuild.1"
}

variable "tags" {
  description = "A map of tags to assign to the resource"
  type        = map(string)
  default     = {}
}