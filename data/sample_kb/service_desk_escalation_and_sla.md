# IT Service Desk Escalation and SLA Guide

## Response and Resolution Targets
P1: response within 15 minutes, resolution target 4 hours, updates every 30 minutes. P2: response within 1 hour, resolution target 8 hours. P3: response within 4 hours, resolution target 3 business days. P4: response within 1 business day, resolution target 5 business days.

## Escalation Path
Tier 1 Service Desk handles initial triage and known fixes. Unresolved tickets go to Tier 2 for endpoint, network, or application specialists. Tier 3 engineering handles complex defects and infrastructure faults. Security incidents go directly to the Security team regardless of tier.

## When to Escalate
Escalate when an SLA is at risk, when multiple users report the same problem, when a fix requires administrator privileges, or when a ticket involves possible data exposure. Include the affected users, error messages, steps already tried, and the time the issue started.

## Major Incident Process
For a P1 outage, the Service Desk lead declares a major incident and opens a bridge call. An incident manager is assigned, and status updates are posted to the internal status page. After resolution, a post-incident review is completed within five business days.

## Ticket Quality Checklist
Good tickets state the affected system, the impact, the exact error text, a screenshot if possible, and the steps to reproduce. Avoid closing a ticket until the user confirms the issue is resolved. Tickets awaiting user response for five business days may be closed automatically.

## Common Requests and Priority Examples
Password reset failure for one user is P3. A team unable to reach a critical application with no workaround is P2. A confirmed ransomware alert is P1. A request for a new monitor is P4.
