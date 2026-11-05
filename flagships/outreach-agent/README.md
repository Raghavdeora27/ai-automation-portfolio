# OA = Outreach Agent

**OA (Outreach Agent)** is my flagship n8n system for cold outreach. It finds out who each prospect is, writes a personal first email with AI, waits for my approval, sends at the right local time, follows up in the same thread and handles every reply. It runs on n8n with Google Gemini, uses Google Sheets as the CRM and sends through Gmail.

**Status:** ✅ Built. OA-00 through OA-06 were live-tested end to end on self-hosted n8n 2.8.4 (4–5 Nov 2026) and passed. Still untested: the OA-99 alert email, the webhook intake, and OA-04 follow-up 2 → no_response. Details [below](#test-status).

## What you get (the instant value)

- **No prospect goes unresearched.** Every first email starts from something real on the prospect's own website, not a mail-merge template.
- **Nothing goes out without a yes.** Every draft comes to my Gmail to approve, edit or reject before it's sent.
- **No duplicates.** A prospect is matched by email and by company domain, so nobody is added twice or emailed twice.
- **No forgotten follow-ups.** Up to two short follow-ups go out in the same thread, and they stop the moment someone replies.
- **Replies don't sit unread.** Each reply is sorted (interested, question, objection, not now, unsubscribe, out of office, bounce) and gets the right next step.
- **Safe sending.** Emails go out only in the prospect's business hours, under a daily cap, and never to anyone on the suppression list.
- **A full audit trail.** Every decision is written to an Events tab, and every failure is written to an Errors tab and sent to me as an alert.
- **A weekly report.** Every Monday I get sent, replies, reply rate and bounces, plus a short AI insight.

## Where this is used

I ran outreach and candidate pipelines by hand as Outreach Manager at DataisGood and as a Consultant at Careernet, where following up on time was most of the job. OA is how I'd run that work now: the research and drafts are automatic, I approve every email, and no follow-up is missed.

## How it works, step by step

Eight n8n workflows share one Google Sheet. The `status` column on the Prospects tab is the queue between them, so each workflow is small, runs on its own schedule, and is safe to re-run.

| Step | Workflow | What happens | Skills involved |
| --- | --- | --- | --- |
| 1 | **OA-00 · Form Intake** | A form to add one prospect by hand. It maps the fields and calls OA-01 by workflow ID, then shows whether the prospect was added. | n8n Form Trigger, Execute Workflow, form UX |
| 2 | **OA-01 · Outreach Intake** | Takes prospects from three places: the form, a webhook (secret header, fails closed) and rows pasted into the sheet. It normalises and validates them, removes duplicates by email and domain, checks suppression, writes `new` and logs every decision to Events. | Multi-channel intake, webhook security, data cleaning, dedupe, audit logging |
| 3 | **OA-02 · Research & Draft** | Every 30 minutes it takes a batch of `new` prospects and fetches each website. A Gemini agent (structured output parser, plus a Sheets tool for history) judges fit and writes an 80–120 word email. A quality score gates weak drafts, which are regenerated or disqualified. If the website or the AI step fails, the prospect is marked `research_failed` and a row is written to Errors. | Web scraping, AI agent with tools, structured output, prompt design, quality gates |
| 4 | **OA-03 · Approval & Send** | Lane A sends each draft to my Gmail with Approve, Approve with edits and Reject. Lane B sends approved emails inside the prospect's local business hours, under the daily cap, after a last suppression check. | Human-in-the-loop (Gmail send-and-wait), timezone logic, rate limiting |
| 5 | **OA-04 · Follow-ups** | Every hour it checks the Gmail thread. If there's a reply, it marks the prospect `replied`. If not, Gemini writes a 2–3 line follow-up in the same thread (`followup_1`, then `followup_2`, then `no_response`). | Gmail threading, scheduling, stop-on-reply logic |
| 6 | **OA-05 · Inbox Agent** | A Gmail trigger matches each reply to its prospect. A Gemini classifier routes it by category. Interested replies and questions get a suggested reply for me to approve. Unsubscribes and bounces are suppressed, and out-of-office replies reschedule the follow-up. | AI classification, Switch routing, suppression handling |
| 7 | **OA-06 · Weekly Report** | Every Monday it emails me the week's metrics and a 3-line Gemini insight. | Reporting, metrics from sheet data |
| 8 | **OA-99 · Error Handler** | It is the error workflow for OA-00 to OA-06. On any failure it sends a Gmail alert and adds an Errors row with the node, the message and an execution link. | Central error handling. Sheets, Gmail and website fetches retry 3 times (2–5 s). Gemini and the AI agent or chain nodes retry 4 times, 5 s apart. |

Diagram, status lifecycle and design decisions: [ARCHITECTURE.md](ARCHITECTURE.md).

## Test status

| What | Status |
| --- | --- |
| OA-00 · Form Intake: add a prospect, and reject a duplicate | ✅ Tested |
| OA-01 · Outreach Intake: sheet import (new row added, duplicate rejected) and the Events log | ✅ Tested |
| OA-01 · Outreach Intake: webhook | ⏳ Built. Not tested yet. |
| OA-02 · Research & Draft: research, draft, and the Errors row it writes when research fails | ✅ Tested |
| OA-03 · Approval & Send: approve with edits, reject, and send | ✅ Tested |
| OA-04 · Follow-ups: follow-up 1 in the same thread | ✅ Tested |
| OA-04 · Follow-ups: follow-up 2, then no_response | ⏳ Built. Not tested yet. Only follow-up 1 was run. |
| OA-05 · Inbox Agent: match a reply, classify it, approve the suggested reply, send it in the thread, status `in_conversation` | ✅ Tested |
| OA-06 · Weekly Report | ✅ Tested |
| OA-99 · Error Handler: alert email | ⏳ Built and set as the error workflow for OA-00 to OA-06. The alert email is not tested yet. OA-02's own error branch writes the Errors row, and that part is tested. |

The steps for each test are in [SETUP.md](SETUP.md#7-six-test-cases-do-these-before-recording).

## What's in this folder

| Path | What it is |
| --- | --- |
| `workflows/OA-00-form-intake.json` … `OA-06-weekly-report.json`, `OA-99-error-handler.json` | The eight n8n exports. They have no credentials and no real IDs: workflow IDs, the sheet ID and email addresses are placeholders. |
| `SETUP.md` | Import order, credentials, the Config table, the webhook secret, six test cases and a demo shot list. |
| `ARCHITECTURE.md` | The mermaid diagram, status lifecycle, design decisions and known limits. |
| `sheet-template/` | The CRM workbook (`.xlsx`) and one CSV header file per tab: Prospects, Messages, Events, Suppression, Errors. |
| `sample-prospects.csv` | 8 fictional test prospects, including one duplicate email and one duplicate domain. |
| `validate_workflows.py` | An offline validator. It checks node types and versions, parameters, connections, `$('Node')` references, retries, Code syntax and secret-looking strings. Run it with `python3 validate_workflows.py [workflows_dir] [n8n_install_dir ...]`. |
| `generator/` | The Python that generates the JSON files. Run `python3 generator/build_all.py` to rebuild them. |

## Setup in short

1. Import OA-99, then OA-01, then OA-00, then OA-02 to OA-06.
2. Replace the two workflow-ID placeholders: `REPLACE_WITH_OA99_ERROR_HANDLER_WORKFLOW_ID` (Settings → Error workflow in OA-00 to OA-06) and `REPLACE_WITH_OA01_INTAKE_WORKFLOW_ID` (the **Run OA-01 Intake** node in OA-00).
3. Fill `YOUR_GOOGLE_SHEET_ID` and the `you@` / `approver@` / `alerts@yourdomain.com` addresses in each Config node.
4. Set the `OUTREACH_WEBHOOK_SECRET` environment variable for the webhook.

Full steps: [SETUP.md](SETUP.md).
