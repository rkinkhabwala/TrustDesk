# Business Continuity and Disaster Recovery Policy

## Architecture

The Harborline platform runs in AWS across multiple availability zones in the us-east-1 region, with a warm standby environment in us-west-2 for disaster recovery.

## Backups

Production databases are backed up continuously with point-in-time recovery, and full snapshots are taken daily. Backups are encrypted, copied to the us-west-2 region, and retained for 35 days.

## Recovery objectives

Harborline's recovery point objective (RPO) is 1 hour and its recovery time objective (RTO) is 4 hours for the production platform.

## Testing

Backup restoration is tested quarterly. A full disaster recovery failover test to us-west-2 is performed at least annually, and the results are documented.

## Business continuity

A business continuity plan covers loss of office facilities and key personnel. All employees can work remotely.
