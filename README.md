# AI SDR Agent

An autonomous B2B sales development agent that researches prospects, writes personalised cold email sequences, sends them via Gmail, classifies replies with AI, and pings Slack when a meeting gets booked — all without a human in the loop.

---

## What it does

```
Prospect in → Research → Write 3-email sequence → Send (Gmail) → Poll replies → Classify → Notify (Slack)
                                                         ↑
                                              n8n triggers follow-ups on day 3 & day 7
```

| Step | Agent / Service | Detail |
|------|----------------|--------|
| **Research** | Researcher Agent | Tavily web search + website scrape → Groq LLM → company summary, pain points, personalisation hooks |
| **Write** | Writer Agent | PAS cold email + value-add follow-up + break-up email, tone calibrated by seniority (C-level / VP / Manager) |
| **Send** | Gmail API | Rate-limited to ~40 emails/hour. Threads follow-ups in the same Gmail conversation |
| **Schedule** | n8n | Follow-up 1 on day 3, follow-up 2 on day 7, reply polling every 15 min |
| **Classify** | Classifier Agent | Groq categorises replies: `interested` / `not_now` / `out_of_office` / `unsubscribe` / `other` |
| **Notify** | Slack webhook | Fires when a prospect is marked `booked` (interested reply detected) |

---

## Tech stack

- **Backend** — Python 3.11, FastAPI, SQLite (aiosqlite/SQLAlchemy async)
- **LLM** — [Groq](https://groq.com) running `llama-3.3-70b-versatile`
- **Web research** — [Tavily](https://tavily.com) search API
- **Email** — Gmail API (OAuth 2.0)
- **Automation** — [n8n](https://n8n.io) (self-hosted)
- **Frontend** — Next.js 14, Tailwind CSS
- **Notifications** — Slack incoming webhook

---

## Prospect lifecycle

```
pending → researched → email_drafted → sent → replied → booked
                                         └──────────────→ unsubscribed
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Cloud project with the **Gmail API** enabled
- A [Groq](https://console.groq.com) API key (free tier works)
- A [Tavily](https://tavily.com) API key (free tier works)
- n8n (Docker recommended, or cloud)
- A Slack workspace with an incoming webhook URL

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/AaditPani-RVU/ai-sdr-agent.git
cd ai-sdr-agent
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the env template and fill in your keys:

```bash
cp .env.example .env
```

```env
# backend/.env
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
SENDER_EMAIL=you@gmail.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
BOOKING_LINK=https://calendly.com/your-link   # optional
DRY_RUN=false   # set true to skip actual sending during testing
```

### 3. Google OAuth (Gmail API)

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**
2. Create an **OAuth 2.0 Client ID** (Desktop app)
3. Download the JSON — rename it to `credentials.json` and place it in `backend/`  
   *(See `backend/credentials.json.example` for the expected shape)*
4. Enable the **Gmail API** for your project

On first run, a browser window will open asking you to authorise the app. A `token.json` file is written to `backend/` and reused on subsequent runs. Both files are gitignored.

### 4. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at `http://localhost:3000`.

### 6. n8n workflows

Import the four workflow files from `n8n/workflows/` into your n8n instance:

| File | Trigger | What it does |
|------|---------|-------------|
| `01_followup_scheduler.json` | Weekdays 9 am | Calls `/prospects/trigger-followups` — sends day-3 and day-7 follow-ups |
| `02_reply_poller.json` | Every 15 min | Calls `/replies/inbox` — reads Gmail, classifies replies, updates statuses |
| `03_booked_notifier.json` | Weekdays 5 pm | Calls `/prospects/` — posts a Slack summary of all booked prospects |
| `04_google_calendar_sync.json` | Webhook / manual | Syncs booked meetings to Google Calendar |

Before importing, replace `YOUR_SLACK_WEBHOOK_URL` in each workflow with your actual Slack webhook URL.

If you're running n8n via Docker, the backend is reachable at `http://host.docker.internal:8000`.

---

## Running a campaign (end-to-end)

### Step 1 — Create a campaign

```bash
curl -X POST http://localhost:8000/campaigns/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Q3 Outbound", "sender_name": "Your Name", "sender_email": "you@gmail.com"}'
```

### Step 2 — Add prospects (CSV bulk upload)

CSV columns: `first_name, last_name, email, role, company, website_url, linkedin_url`

```bash
curl -X POST "http://localhost:8000/prospects/bulk?campaign_id=1" \
  -F "file=@prospects.csv"
```

### Step 3 — Research a prospect

```bash
curl -X POST http://localhost:8000/prospects/1/research
```

### Step 4 — Draft the 3-email sequence

```bash
curl -X POST http://localhost:8000/prospects/1/draft
```

### Step 5 — Review & send

View the draft at `http://localhost:3000` or via:

```bash
curl http://localhost:8000/prospects/1/draft
```

Send when happy:

```bash
curl -X POST http://localhost:8000/prospects/1/send
```

n8n takes over from here — follow-ups go out automatically on day 3 and day 7.

---

## API reference

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/campaigns/` | Create campaign |
| `GET` | `/campaigns/` | List all campaigns with stats |
| `POST` | `/prospects/` | Add single prospect |
| `POST` | `/prospects/bulk?campaign_id=N` | CSV bulk import |
| `GET` | `/prospects/` | List prospects (filter by `campaign_id`) |
| `POST` | `/prospects/{id}/research` | Run researcher agent |
| `POST` | `/prospects/{id}/draft` | Run writer agent |
| `GET` | `/prospects/{id}/draft` | Fetch current draft |
| `POST` | `/prospects/{id}/send` | Send initial email |
| `POST` | `/prospects/{id}/send-followup` | Send next follow-up manually |
| `POST` | `/prospects/trigger-followups` | Bulk follow-up trigger (called by n8n) |
| `POST` | `/prospects/find-contacts` | Discover contacts at a company via web search |
| `GET` | `/replies/inbox` | Poll Gmail, classify replies, update statuses |
| `POST` | `/replies/classify` | Classify a single reply body |
| `GET` | `/health` | Health check |

Full interactive docs: `http://localhost:8000/docs`

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for LLM inference |
| `TAVILY_API_KEY` | Yes | Tavily API key for web research |
| `SENDER_EMAIL` | Yes | Gmail address to send from |
| `SLACK_WEBHOOK_URL` | Yes | Slack incoming webhook for booked notifications |
| `BOOKING_LINK` | No | Calendly/Cal.com URL appended to email footers |
| `DRY_RUN` | No | Set `true` to skip actual Gmail sending (default: `false`) |

---

## Project structure

```
ai-sdr-agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── researcher.py     # Tavily search + Groq research
│   │   │   ├── writer.py         # 3-email sequence generator
│   │   │   ├── classifier.py     # Reply classifier
│   │   │   ├── sender.py         # Gmail send + rate limiting
│   │   │   └── contact_finder.py # Web-based contact discovery
│   │   ├── routes/
│   │   │   ├── campaigns.py
│   │   │   ├── prospects.py
│   │   │   ├── replies.py
│   │   │   └── webhooks.py
│   │   ├── services/
│   │   │   ├── groq_client.py    # Groq async wrapper
│   │   │   ├── gmail_service.py  # Gmail API helpers
│   │   │   ├── slack_service.py  # Slack notifications
│   │   │   └── calendar_service.py
│   │   ├── db.py                 # SQLAlchemy async models
│   │   ├── schemas.py            # Pydantic schemas
│   │   └── main.py
│   ├── credentials.json.example  # Copy → credentials.json, fill in OAuth details
│   └── requirements.txt
├── frontend/
│   └── app/
│       ├── page.tsx              # Dashboard (stats + campaigns)
│       └── campaigns/page.tsx    # Campaign management
├── n8n/
│   └── workflows/
│       ├── 01_followup_scheduler.json
│       ├── 02_reply_poller.json
│       ├── 03_booked_notifier.json
│       └── 04_google_calendar_sync.json
└── .env.example
```

---

## Notes

- **Rate limiting** — the sender waits 90 seconds between emails (~40/hour) to avoid Gmail spam filters.
- **Dry run mode** — set `DRY_RUN=true` in `.env` to test the full pipeline without sending any real email.
- **Token refresh** — `token.json` is refreshed automatically by the Google auth library. If it ever breaks, delete the file and re-run to re-authorise.
- **SQLite** — the default database is a local `sdr.db` file. For production, swap the `DATABASE_URL` in `db.py` for a Postgres connection string.
