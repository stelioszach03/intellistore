# IntelliStore Vault Configuration

This directory contains Terraform modules and Helm charts for deploying and configuring HashiCorp Vault for IntelliStore.

## Overview

Vault is used in IntelliStore for:
- Client-side encryption key management
- JWT signing keys for API authentication
- Secret storage for service-to-service communication
- Transit engine for data encryption/decryption

## Structure

```
intellistore-vault-config/
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── policies/
├── helm/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── scripts/
│   ├── bootstrap-vault.sh
│   ├── setup-policies.sh
│   └── init-transit-engine.sh
└── policies/
    ├── api-service.hcl
    ├── client-access.hcl
    └── admin.hcl
```

## Quick Start

### 1. Deploy Vault with Helm

```bash
helm install vault ./helm -f values.yaml
```

### 2. Initialize Vault

```bash
./scripts/bootstrap-vault.sh
```

### 3. Setup Policies and Transit Engine

```bash
./scripts/setup-policies.sh
./scripts/init-transit-engine.sh
```

## Configuration

### Transit Engine

The transit engine is configured with the following keys:
- `intellistore-master`: Master encryption key for data encryption
- `jwt-signing`: Key for JWT token signing
- Per-bucket keys: `bucket-{bucketName}` for bucket-specific encryption

### Policies

#### API Service Policy
- Read/write access to transit engine
- Ability to generate data encryption keys
- Access to JWT signing keys

#### Client Access Policy
- Read-only access to transit engine for their namespace
- Ability to decrypt data they encrypted

#### Admin Policy
- Full access to Vault configuration
- Ability to manage policies and keys

## Security Considerations

1. **Auto-unseal**: Configure auto-unseal with cloud KMS in production
2. **TLS**: Enable TLS for all Vault communications
3. **Audit Logging**: Enable audit logging for compliance
4. **Backup**: Regular backup of Vault data
5. **Key Rotation**: Implement key rotation policies

## Environment Variables

Required environment variables:
- `VAULT_ADDR`: Vault server address
- `VAULT_TOKEN`: Vault root token (for initial setup)
- `VAULT_NAMESPACE`: Vault namespace (Enterprise only)

## Monitoring

Vault metrics are exposed on `/v1/sys/metrics` and can be scraped by Prometheus.

Key metrics to monitor:
- `vault_core_unsealed`: Vault seal status
- `vault_runtime_alloc_bytes`: Memory usage
- `vault_audit_log_request_failure`: Audit log failures
- `vault_token_count`: Active token count