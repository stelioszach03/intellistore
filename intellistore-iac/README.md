# IntelliStore Infrastructure as Code

This directory contains Terraform modules for deploying IntelliStore on various cloud providers.

## Structure

```
intellistore-iac/
├── modules/
│   ├── aws/
│   │   ├── eks/
│   │   ├── vpc/
│   │   └── storage/
│   ├── gcp/
│   │   ├── gke/
│   │   ├── vpc/
│   │   └── storage/
│   └── azure/
│       ├── aks/
│       ├── vnet/
│       └── storage/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
└── scripts/
    ├── deploy.sh
    └── destroy.sh
```

## Quick Start

### AWS EKS

1. Copy the example variables:
   ```bash
   cp environments/dev/aws/terraform.tfvars.example environments/dev/aws/terraform.tfvars
   ```

2. Edit the variables file with your specific values.

3. Initialize and apply:
   ```bash
   cd environments/dev/aws
   terraform init
   terraform plan
   terraform apply
   ```

### GCP GKE

1. Copy the example variables:
   ```bash
   cp environments/dev/gcp/terraform.tfvars.example environments/dev/gcp/terraform.tfvars
   ```

2. Edit the variables file with your specific values.

3. Initialize and apply:
   ```bash
   cd environments/dev/gcp
   terraform init
   terraform plan
   terraform apply
   ```

### Azure AKS

1. Copy the example variables:
   ```bash
   cp environments/dev/azure/terraform.tfvars.example environments/dev/azure/terraform.tfvars
   ```

2. Edit the variables file with your specific values.

3. Initialize and apply:
   ```bash
   cd environments/dev/azure
   terraform init
   terraform plan
   terraform apply
   ```

## Prerequisites

- Terraform >= 1.0
- Cloud provider CLI tools (aws, gcloud, az)
- kubectl
- helm

## Security

- All resources are created with security best practices
- Network policies are enabled by default
- RBAC is configured for least privilege access
- Encryption at rest and in transit is enabled

## Monitoring

- Prometheus and Grafana are deployed by default
- CloudWatch/Stackdriver/Azure Monitor integration
- Custom dashboards for IntelliStore metrics

## Backup and Disaster Recovery

- Automated backups for persistent volumes
- Cross-region replication for critical data
- Disaster recovery procedures documented