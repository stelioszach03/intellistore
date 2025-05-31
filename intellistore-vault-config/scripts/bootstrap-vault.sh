#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
VAULT_NAMESPACE=${VAULT_NAMESPACE:-"intellistore"}
VAULT_ADDR=${VAULT_ADDR:-"http://localhost:8200"}
INIT_FILE="/tmp/vault-init.json"

echo -e "${GREEN}Starting Vault bootstrap process...${NC}"

# Wait for Vault to be ready
echo -e "${YELLOW}Waiting for Vault to be ready...${NC}"
until curl -s "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; do
    echo "Waiting for Vault..."
    sleep 5
done

echo -e "${GREEN}Vault is ready!${NC}"

# Check if Vault is already initialized
if curl -s "${VAULT_ADDR}/v1/sys/init" | jq -r '.initialized' | grep -q true; then
    echo -e "${YELLOW}Vault is already initialized${NC}"
    
    # Check if we have the init file
    if [[ ! -f "$INIT_FILE" ]]; then
        echo -e "${RED}Vault is initialized but init file not found at $INIT_FILE${NC}"
        echo -e "${RED}Please provide the unseal keys and root token manually${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Initializing Vault...${NC}"
    
    # Initialize Vault
    curl -s -X POST \
        -d '{"secret_shares": 5, "secret_threshold": 3}' \
        "${VAULT_ADDR}/v1/sys/init" > "$INIT_FILE"
    
    echo -e "${GREEN}Vault initialized successfully!${NC}"
    echo -e "${YELLOW}Init data saved to: $INIT_FILE${NC}"
    echo -e "${RED}IMPORTANT: Save the unseal keys and root token securely!${NC}"
fi

# Extract unseal keys and root token
UNSEAL_KEYS=($(jq -r '.keys[]' "$INIT_FILE"))
ROOT_TOKEN=$(jq -r '.root_token' "$INIT_FILE")

echo -e "${YELLOW}Unsealing Vault...${NC}"

# Unseal Vault (need 3 out of 5 keys)
for i in {0..2}; do
    curl -s -X POST \
        -d "{\"key\": \"${UNSEAL_KEYS[$i]}\"}" \
        "${VAULT_ADDR}/v1/sys/unseal" > /dev/null
    echo "Unseal key $((i+1)) applied"
done

# Check if Vault is unsealed
if curl -s "${VAULT_ADDR}/v1/sys/seal-status" | jq -r '.sealed' | grep -q false; then
    echo -e "${GREEN}Vault is unsealed!${NC}"
else
    echo -e "${RED}Failed to unseal Vault${NC}"
    exit 1
fi

# Set root token for subsequent operations
export VAULT_TOKEN="$ROOT_TOKEN"

echo -e "${YELLOW}Configuring Vault...${NC}"

# Enable audit logging
echo "Enabling audit logging..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"type": "file", "options": {"file_path": "/vault/logs/audit.log"}}' \
    "${VAULT_ADDR}/v1/sys/audit/file" || echo "Audit logging may already be enabled"

# Enable transit secrets engine
echo "Enabling transit secrets engine..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"type": "transit"}' \
    "${VAULT_ADDR}/v1/sys/mounts/transit" || echo "Transit engine may already be enabled"

# Enable KV v2 secrets engine for general secrets
echo "Enabling KV v2 secrets engine..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"type": "kv", "options": {"version": "2"}}' \
    "${VAULT_ADDR}/v1/sys/mounts/secret" || echo "KV v2 engine may already be enabled"

# Create master encryption key
echo "Creating master encryption key..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"type": "aes256-gcm96"}' \
    "${VAULT_ADDR}/v1/transit/keys/intellistore-master" || echo "Master key may already exist"

# Create JWT signing key
echo "Creating JWT signing key..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"type": "rsa-2048"}' \
    "${VAULT_ADDR}/v1/transit/keys/jwt-signing" || echo "JWT signing key may already exist"

# Create a policy for the API service
echo "Creating API service policy..."
cat > /tmp/api-service-policy.hcl << 'EOF'
# Transit engine access for encryption/decryption
path "transit/encrypt/intellistore-master" {
  capabilities = ["create", "update"]
}

path "transit/decrypt/intellistore-master" {
  capabilities = ["create", "update"]
}

path "transit/encrypt/bucket-*" {
  capabilities = ["create", "update"]
}

path "transit/decrypt/bucket-*" {
  capabilities = ["create", "update"]
}

path "transit/keys/bucket-*" {
  capabilities = ["create", "update", "read"]
}

# JWT signing
path "transit/sign/jwt-signing" {
  capabilities = ["create", "update"]
}

path "transit/verify/jwt-signing" {
  capabilities = ["create", "update"]
}

# General secrets access
path "secret/data/intellistore/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/intellistore/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

curl -s -X PUT \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d "{\"policy\": \"$(cat /tmp/api-service-policy.hcl | sed 's/"/\\"/g' | tr '\n' ' ')\"}" \
    "${VAULT_ADDR}/v1/sys/policies/acl/api-service"

# Create a policy for client access
echo "Creating client access policy..."
cat > /tmp/client-access-policy.hcl << 'EOF'
# Allow clients to encrypt/decrypt with their bucket keys
path "transit/encrypt/bucket-{{identity.entity.aliases.auth_userpass_*.name}}-*" {
  capabilities = ["create", "update"]
}

path "transit/decrypt/bucket-{{identity.entity.aliases.auth_userpass_*.name}}-*" {
  capabilities = ["create", "update"]
}

# Allow clients to read their own secrets
path "secret/data/intellistore/users/{{identity.entity.aliases.auth_userpass_*.name}}/*" {
  capabilities = ["read"]
}
EOF

curl -s -X PUT \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d "{\"policy\": \"$(cat /tmp/client-access-policy.hcl | sed 's/"/\\"/g' | tr '\n' ' ')\"}" \
    "${VAULT_ADDR}/v1/sys/policies/acl/client-access"

# Enable userpass auth method
echo "Enabling userpass auth method..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"type": "userpass"}' \
    "${VAULT_ADDR}/v1/sys/auth/userpass" || echo "Userpass auth may already be enabled"

# Create a service account for the API service
echo "Creating API service account..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"password": "api-service-password", "policies": "api-service"}' \
    "${VAULT_ADDR}/v1/auth/userpass/users/api-service"

# Store the API service credentials in a secret
echo "Storing API service credentials..."
curl -s -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -d '{"data": {"username": "api-service", "password": "api-service-password"}}' \
    "${VAULT_ADDR}/v1/secret/data/intellistore/api-service/credentials"

echo -e "${GREEN}Vault bootstrap completed successfully!${NC}"
echo -e "${YELLOW}Important information:${NC}"
echo -e "Root Token: ${RED}$ROOT_TOKEN${NC}"
echo -e "Vault Address: $VAULT_ADDR"
echo -e "Init file: $INIT_FILE"
echo -e "${RED}Please save the root token and unseal keys securely!${NC}"

# Clean up temporary files
rm -f /tmp/api-service-policy.hcl /tmp/client-access-policy.hcl