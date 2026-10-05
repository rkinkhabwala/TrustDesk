# Access Control Policy

## Authentication

All workforce access to production systems and internal applications goes through the corporate single sign-on (SSO) provider. Multi-factor authentication (MFA) is required for all employees and contractors for every application connected to SSO. SMS is not permitted as an MFA factor; employees use hardware security keys or an authenticator app.

Customer accounts in the Harborline platform support SAML 2.0 SSO and optional TOTP-based MFA, which customer administrators can enforce for their users.

## Least privilege

Access is granted on a least-privilege basis according to job role. Requests for access are made through the ticketing system and require approval from the employee's manager and the system owner.

## Privileged access

Engineers do not have standing administrative access to production. Production administrative access is granted just-in-time for a maximum of 4 hours, requires a linked change or incident ticket, and every session is logged.

## Access reviews

System owners review user access to production systems and systems containing customer data every quarter. Inappropriate access found during a review is removed within 5 business days.

## Termination

When an employee or contractor leaves, all access is revoked within 24 hours of their last working day, triggered automatically from the HR system.

## Passwords

Where passwords are used, they must be at least 14 characters long. Passwords are stored only as salted hashes using bcrypt.
