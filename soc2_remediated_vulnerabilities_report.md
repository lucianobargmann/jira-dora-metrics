# Sample of Remediated Vulnerabilities
## SOC 2 Evidence — Observation Period: March–April 2026

**Prepared by:** Luciano Bargmann  
**Date:** 2026-04-22  
**Source:** Bitbucket Pull Requests (dcoya workspace)

---

## Summary

The following sample documents high-severity vulnerabilities identified and remediated through our development process during the most recent observation period. Each entry includes the Jira ticket reference, the nature of the vulnerability, and the pull request demonstrating remediation.

---

## 1. Authentication Bypass — Unauthenticated Access to Secure-Login Customer Resources

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-754 |
| **Severity** | High |
| **Category** | Broken Authentication |
| **Description** | An unauthenticated bypass was discovered for secure-login customers, allowing potential unauthorized access to customer file serving endpoints. |
| **Remediation PR** | [nemo #3886](https://bitbucket.org/dcoya/nemo/pull-requests/3886) — `fix(SAOP2-754): remove unauthenticated bypass for secure-login customers` |
| **Author** | jleahy |
| **Date Merged** | 2026-04-09 |
| **Staging PR** | [nemo #3836](https://bitbucket.org/dcoya/nemo/pull-requests/3836) |

---

## 2. Authorization Flaw — Missing Auth Check in Customer File Serving

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-822 |
| **Severity** | High |
| **Category** | Broken Access Control |
| **Description** | A vulnerability was identified where the auth check was not properly enforced before cookie/query param validation in the customer file serving endpoint, potentially allowing unauthorized file access. |
| **Remediation PR** | [nemo #3907](https://bitbucket.org/dcoya/nemo/pull-requests/3907) — `fix(SAOP2-822): restore auth check before cookie/query param in customer file serving` |
| **Author** | Luis Felipe Cordeiro Sena |
| **Date Merged** | 2026-04-13 |

---

## 3. CSRF/CORS Misconfiguration — Missing Trusted Origins for Production EU

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-772, SAOP2-781 |
| **Severity** | High |
| **Category** | Security Misconfiguration |
| **Description** | Production EU hostnames were missing from ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, and CORS_ALLOWED_ORIGINS, leaving the EU deployment exposed to potential cross-origin and CSRF attacks. |
| **Remediation PRs** | [nemo #3797](https://bitbucket.org/dcoya/nemo/pull-requests/3797) — `Fix: add prod-eu hostnames to ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, and CORS_ALLOWED_ORIGINS` |
| | [nemo #3814](https://bitbucket.org/dcoya/nemo/pull-requests/3814) — `Fix: add legacy EU hostname to ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, and CORS_ALLOWED_ORIGINS` |
| **Author** | Matheus Batistela |
| **Dates Merged** | 2026-03-24, 2026-03-26 |

---

## 4. TLS/SSL Deprecation — Deprecated Connection Options in DocumentDB

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-807 |
| **Severity** | Medium |
| **Category** | Cryptographic Failures |
| **Description** | Mongoose connection was using deprecated `ssl` option instead of `tls` for DocumentDB compatibility, potentially causing connection instability and non-compliance with current TLS standards. |
| **Remediation PR** | [nemo #3852](https://bitbucket.org/dcoya/nemo/pull-requests/3852) — `Update mongoose connection options from deprecated ssl to tls for DocumentDB compatibility` |
| **Author** | Matheus Batistela |
| **Date Merged** | 2026-04-06 |

---

## 5. Silent Scan Engine Failure — Security Scanning Results Not Reaching Backend

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-807 |
| **Severity** | High |
| **Category** | Logging & Monitoring Failures |
| **Description** | A silent failure across all Node.js scanning engines was preventing scan results from reaching the Django backend, meaning security scan findings were being silently dropped. |
| **Remediation PR** | [nemo #3947](https://bitbucket.org/dcoya/nemo/pull-requests/3947) — `Fix silent failure across all Node.js scanning engines preventing scan results from reaching Django` |
| **Author** | jleahy |
| **Date Merged** | 2026-04-16 |

---

## 6. Authentication Pipeline — Case-Insensitive Email Handling

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-749 |
| **Severity** | Medium |
| **Category** | Broken Authentication |
| **Description** | Employee association was not being created for admin-turned-learner users due to case-sensitive email comparison in the User Portal auth pipeline, potentially locking users out. |
| **Remediation PR** | [nemo #3864](https://bitbucket.org/dcoya/nemo/pull-requests/3864) — `fix employee association not created for admin-turned-learner users, add case-insensitive email handling across User Portal auth pipeline` |
| **Author** | jleahy |
| **Date Merged** | 2026-04-09 |

---

## 7. Magic Link Account Creation — Offboarded Customer Exploitation

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-743 |
| **Severity** | High |
| **Category** | Broken Access Control |
| **Description** | Magic link authentication could create new user accounts linked to offboarded (deactivated) customer tenants, potentially allowing unauthorized access to residual data. |
| **Remediation PR** | [nemo #3790](https://bitbucket.org/dcoya/nemo/pull-requests/3790) — `prevent magic link from creating users linked to offboarded customers` |
| **Author** | jleahy |
| **Date Merged** | 2026-03-23 |

---

## 8. WAF Deployment — Web Application Firewall for Production

| Field | Detail |
|-------|--------|
| **Ticket** | Infrastructure |
| **Severity** | High |
| **Category** | Security Hardening |
| **Description** | Deployment of WAF (Web Application Firewall) module across production environments to protect against common web exploits (OWASP Top 10). |
| **Remediation PR** | [ninjio-infra #95](https://bitbucket.org/dcoya/ninjio-infra/pull-requests/95) — `add WAF module, phish-training-2 ALB, ECS scaling scripts, and config updates` |
| **Author** | Carlos Nilton Araújo Corrêa |
| **Date Merged** | 2026-04-12 |

---

## 9. CORS Preflight Rejection — Reporter Button Security Fix

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-567 |
| **Severity** | Medium |
| **Category** | Security Misconfiguration |
| **Description** | CORS preflight requests were being rejected for the Reporter Button, and settings load order was causing security configuration to not apply correctly. |
| **Remediation PR** | [nemo #3794](https://bitbucket.org/dcoya/nemo/pull-requests/3794) — `fix(SAOP2-567) CORS preflight rejected for Reporter Button, settings load order` |
| **Author** | Rai Tamarindo |
| **Date Merged** | 2026-03-24 |

---

## 10. MFA Implementation — Multi-Factor Authentication Support

| Field | Detail |
|-------|--------|
| **Ticket** | SAOP2-834 |
| **Severity** | High |
| **Category** | Security Enhancement |
| **Description** | Added multi-factor authentication (MFA) support to strengthen user authentication and prevent unauthorized access. |
| **Remediation PR** | [ninjio-reporter-workers #29](https://bitbucket.org/dcoya/ninjio-reporter-workers/pull-requests/29) — `SAOP2-834 - adding MFA support` |
| **Author** | Fabio Rodrigues |
| **Date Merged** | 2026-04-20 |

---

## Process Notes

- All vulnerabilities were tracked via Jira tickets (SAOP2-xxx prefix)
- Fixes went through code review and pull request process in Bitbucket
- Remediation PRs were merged to staging, validated, then promoted to production
- Infrastructure security changes (WAF, TLS) managed via Terraform in the `ninjio-infra` repository
