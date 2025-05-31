# IntelliStore Vault Policy
# This policy allows the IntelliStore API to access secrets

path "intellistore/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/data/intellistore/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/intellistore/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Allow token renewal
path "auth/token/renew-self" {
  capabilities = ["update"]
}

# Allow token lookup
path "auth/token/lookup-self" {
  capabilities = ["read"]
}