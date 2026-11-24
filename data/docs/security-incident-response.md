# Security Incident Response

Owner: Security Team · Applies to: all employees and on-call engineers

## What Counts as an Incident

A security incident is any event that may compromise the confidentiality, integrity, or availability of company or customer data. Examples include lost devices, malware, leaked credentials, unauthorized access, and data sent to the wrong recipient.

## Severity Levels

SEV1 means confirmed exposure of Restricted data or a production breach; the Security on-call engineer must acknowledge within 15 minutes. SEV2 means a likely compromise of a single account or device, with acknowledgement within 1 hour. SEV3 covers suspicious activity without confirmed impact, handled within one business day.

## Reporting an Incident

Report incidents by paging Security on-call through PagerDuty with the service name "security-incident", or post in #security-help if you are unsure. Do not try to investigate on your own, delete evidence, or power off an affected machine.

## After an Incident

Every SEV1 and SEV2 incident gets a blameless postmortem within five business days. Customer notification decisions are made by Legal and the Chief Information Security Officer, never by individual employees.
