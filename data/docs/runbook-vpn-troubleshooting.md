# Runbook: VPN Connection Troubleshooting

Owner: IT Department · Audience: employees and IT service desk

## Symptoms

Use this runbook when GlobalProtect shows "Not Connected", gets stuck on "Connecting", or connects but internal sites such as the wiki do not load.

## Quick Fixes

First, confirm your internet works by opening a public website. Next, quit GlobalProtect completely and reopen it. If that fails, switch to a different gateway from the gateway menu. Make sure your system clock is correct, because a wrong clock causes certificate errors. Restart your laptop if the client still will not connect.

## Error Messages

"Authentication failed" usually means an expired password; reset it on a non-VPN network through id.corvane.example from the office, or call the service desk. "Gateway not responding" usually means a regional outage; check the #it-status Slack channel. "Required client certificate not found" means the device profile is broken and IT must reinstall it.

## Escalation

If none of these steps work, open an IT service desk ticket with your laptop's asset tag, the gateway you used, a screenshot of the error, and the time it happened. Service desk escalates to the Network team after 30 minutes without a fix.
