# Secure Software Development Policy

## Code review

All code changes to production services require review and approval by at least one engineer other than the author before merging. Direct pushes to the main branch are blocked.

## Automated security testing

Static application security testing (SAST) and software dependency scanning run on every pull request in the CI pipeline. Builds with critical findings cannot be deployed.

## Environments

Development, staging and production environments are separated. Production customer data is never used in development or testing environments.

## Penetration testing

An independent third-party firm performs a penetration test of the Harborline platform at least annually. A summary letter is available to customers under NDA.

## Vulnerability management

Production infrastructure is scanned for vulnerabilities weekly. Vulnerabilities are remediated within these timelines: critical within 7 days, high within 30 days, medium within 90 days.

## Change management

Production changes are deployed through the CI/CD pipeline, are linked to a ticket, and can be rolled back.
