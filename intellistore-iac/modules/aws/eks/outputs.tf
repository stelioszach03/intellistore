output "cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.intellistore.id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.intellistore.arn
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.intellistore.endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_eks_cluster.intellistore.vpc_config[0].cluster_security_group_id
}

output "cluster_iam_role_name" {
  description = "IAM role name associated with EKS cluster"
  value       = aws_iam_role.cluster.name
}

output "cluster_iam_role_arn" {
  description = "IAM role ARN associated with EKS cluster"
  value       = aws_iam_role.cluster.arn
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.intellistore.certificate_authority[0].data
}

output "cluster_primary_security_group_id" {
  description = "The cluster primary security group ID created by EKS"
  value       = aws_eks_cluster.intellistore.vpc_config[0].cluster_security_group_id
}

output "cloudwatch_log_group_name" {
  description = "Name of cloudwatch log group created"
  value       = aws_cloudwatch_log_group.cluster.name
}

output "cloudwatch_log_group_arn" {
  description = "Arn of cloudwatch log group created"
  value       = aws_cloudwatch_log_group.cluster.arn
}

output "node_groups" {
  description = "EKS node groups"
  value       = aws_eks_node_group.intellistore
}

output "node_security_group_arn" {
  description = "Amazon Resource Name (ARN) of the node shared security group"
  value       = aws_eks_cluster.intellistore.vpc_config[0].cluster_security_group_id
}

output "node_security_group_id" {
  description = "ID of the node shared security group"
  value       = aws_eks_cluster.intellistore.vpc_config[0].cluster_security_group_id
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider if enabled"
  value       = aws_iam_openid_connect_provider.cluster.arn
}

output "cluster_tls_certificate_sha1_fingerprint" {
  description = "The SHA1 fingerprint of the public key of the cluster's certificate"
  value       = data.tls_certificate.cluster.certificates[0].sha1_fingerprint
}