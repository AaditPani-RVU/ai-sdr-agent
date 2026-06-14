# n8n Workflows

Import these from `workflows/` into your n8n instance (Settings → Import workflow).

| File | Trigger | What it does |
|---|---|---|
| `01_followup_scheduler.json` | Weekdays 9 AM | Calls `POST /prospects/trigger-followups` — backend sends FU1 at day 3 and FU2 at day 7 for all eligible prospects |
| `02_reply_poller.json` | Every 15 min | Calls `GET /replies/inbox` — classifies unread Gmail replies, updates prospect status, marks as read |
| `03_booked_notifier.json` | Weekdays 5 PM | Fetches all prospects, filters for `booked` status, posts daily digest to Slack |

## Setup

1. Run n8n: `npx n8n` or via Docker
2. Import each workflow JSON
3. For `03_booked_notifier.json`: set `SLACK_WEBHOOK_URL` as an n8n environment variable (Settings → Environment Variables)
4. Activate each workflow

> **Note:** The backend also fires a real-time Slack notification the moment a prospect is classified as "interested" via `/replies/inbox`, if `SLACK_WEBHOOK_URL` is set in `backend/.env`. The n8n booked notifier is a complementary daily digest.
