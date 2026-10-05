# Encryption and Key Management Policy

## Data at rest

All customer data at rest, including databases, object storage, backups and log archives, is encrypted with AES-256 using AWS Key Management Service (KMS).

## Data in transit

All data in transit over public networks is encrypted with TLS 1.2 or higher. TLS 1.0 and 1.1 are disabled on all public endpoints. Internal service-to-service traffic is also encrypted with TLS.

## Key management

Encryption keys are managed in AWS KMS. Keys are rotated automatically every 12 months. Access to key administration is limited to the infrastructure security team and is logged.

## Customer-managed keys

Harborline does not currently support customer-managed encryption keys (BYOK). All keys are managed by Harborline in AWS KMS.

## Endpoint encryption

All company laptops use full-disk encryption (FileVault on macOS), enforced and monitored through the device management platform.
