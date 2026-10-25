# Security Policy

Verifiko is a URL reputation and phishing/malware detection service. Reports that help keep
it and its users safe are welcome.

## Reporting a vulnerability

Please report vulnerabilities privately by email to **security@verifiko.es**.

Do not open a public GitHub issue, pull request or discussion for a security problem, and
please don't disclose it publicly until a fix has been released.

A useful report includes:

- A description of the issue and its potential impact.
- Steps to reproduce, or a proof of concept.
- The affected component (API endpoint, web app, detection engine) and any relevant URLs,
  requests or payloads.

## What to expect

- An acknowledgement within a few business days.
- An initial assessment and, where the report is confirmed, an estimate of when a fix will
  be available.
- A notice when the fix is deployed.

This is a personal project maintained on a best-effort basis, so these are good-faith
targets rather than guaranteed response times.

## Supported versions

Only the latest `main` branch, which is what runs in production at
[verifiko.es](https://www.verifiko.es), receives security fixes.

## Scope and testing guidelines

When testing, please:

- Use only accounts and API keys you own.
- Avoid degrading the service for others: no denial-of-service, load testing or
  high-volume automated scanning.
- Don't access, modify or keep other users' data. If you come across any, stop and include
  that in your report.
- Don't use social engineering or attack third-party infrastructure (Vercel, Neon, Upstash,
  Resend and others). Report issues in those services to their vendors.

## Coordinated disclosure

Once a fix is released, you are welcome to publish your findings. With your permission,
you will be credited for the report.
