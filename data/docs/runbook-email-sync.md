# Runbook: Email and Calendar Sync Problems

Owner: IT Department · Audience: employees and IT service desk

## Symptoms and Basic Checks

Use this runbook when new email does not appear on your phone, calendar invites are missing, or meeting changes do not show up on one device.

Confirm the problem in Gmail on the web at mail.google.com. If mail appears on the web but not on your phone, the problem is with the phone app. Check that the phone has an internet connection and is not in low power mode, which pauses background sync.

## Fix Mobile Sync

Company email on phones is supported only in the Gmail and Google Calendar apps managed by the Intune profile. Remove and re-add your account in the app. If you recently changed your password, sign in again with the new password and approve the MFA prompt.

## Missing Calendar Invites

Ask the organizer to confirm they invited your correct corvane.example address. Check the "Other calendars" list to ensure your calendar is visible. Invites from external organizers can take up to 15 minutes to appear.

## Escalation

If sync is broken on the web as well, check the #it-status Slack channel for a Google Workspace incident, then open an IT service desk ticket.
