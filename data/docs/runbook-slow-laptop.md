# Runbook: Slow Laptop Performance

Owner: IT Department · Audience: employees and IT service desk

## First Checks

Restart your laptop if it has been running for more than seven days; many slowdowns are fixed by a restart. Check that at least 20 GB of disk space is free. Close unused browser tabs, since each tab can use hundreds of megabytes of memory.

## Find the Cause

On macOS, open Activity Monitor and sort by CPU and then by Memory. On Windows, open Task Manager with Ctrl+Shift+Esc. If the endpoint protection agent is using high CPU for more than 30 minutes, a scheduled scan may be running; scans are scheduled for Wednesdays at noon.

## Updates

Install pending operating system updates from the device management prompt. Laptops more than two major OS versions behind are blocked from company systems until updated.

## Escalation

If your laptop is still slow after these steps, open an IT service desk ticket with screenshots of Activity Monitor or Task Manager and your asset tag. IT can run remote diagnostics. Laptops older than three years qualify for the refresh program described in the Laptop Provisioning policy.
