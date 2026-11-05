# AI Automation Portfolio

Hi, I'm Raghav Deora. I build AI agents and automations on n8n, Make and Zapier that take repetitive work off your team's plate: cold outreach, lead follow-up, invoicing, support replies, approvals and onboarding. You get the hours back. Invoices go out the moment a payment lands, leads stop slipping through the cracks, the same person or invoice never goes in twice, every action leaves an audit trail, and a person still signs off on the decisions that matter.

### Built and run in my own product

I founded [JobRays](https://jobrays.io), an AI career companion. It launched around June 2026 as a global product. I built it myself with Next.js, FastAPI and Supabase, hosted on Vercel: the engines, the backend and frontend, and Ray, its AI career companion chatbot. The business runs on the same kind of automations I build for clients: Razorpay payments, Zoho Books invoicing and bookkeeping (including international transactions), and email automations with Resend and Loops.

### Process first, then automation

Before JobRays, I spent 5+ years in operations and recruitment. As Ops Manager at BlueBox Singapore (until January 2025), I used Lean Six Sigma to cut process variability by 25% before automating anything. Then I saved about 500 hours a year through automation with Flokzu, ClickUp and Zoho. Earlier, I was Outreach Manager at DataisGood (2023–24) and a Consultant at Careernet (2021–23), where I guided 6,000+ candidates from interview to onboarding. I have an MBA and I'm Lean Six Sigma certified. I always fix the process before I automate it, because automating a messy handoff just delivers the mess faster.

### Built for a real week, not a demo

A slow API gets retried. A stored ID stops a second invoice, lead, or email from going out. A person approves the steps that should stay human. If something fails, you hear about it before your customer does.

**What you'll find here:** 3 flagship systems (multi-workflow builds, each with a prefix) and 14 single automations (plain numbers 01–14). Every build here runs on test accounts with fictional sample data. There are no client names or client results in this repo. I add the working export and a demo video as each one is ready to publish.

📅 [Book a call](https://calendar.app.google/xPLZuaDusXaS93v17) to talk through your workflow.

## Prefix key

Every workflow name in this repo and in my n8n, Make and Zapier accounts starts with one of these, so you can tell at a glance which system it belongs to. Flagship workflows use a prefix (`OA-01 · …`); single automations keep their plain number (`02 · …`), so the two never clash.

| Prefix | Stands for | What it is |
| --- | --- | --- |
| **OA** | Outreach Agent | Flagship system on n8n. AI prospect research, personalised cold email I approve, follow-ups and reply handling. Workflows OA-00 to OA-06, plus OA-99. |
| **SA** | Support Agent | Flagship system on n8n. AI inbox triage, answers from your docs, and escalation to a person. Planned. |
| **CRM** | CRM Pipeline | Flagship system on Make + HubSpot. A lead-to-deal pipeline. Planned. |
| **Shared** | Shared utilities | Small helpers that several workflows use, such as `Shared · Error Alert` (it was `00 · Error Alert`). They live in my n8n account; exports to come. |
| **01–14** | Single automations | One focused workflow each, numbered 01 to 14, on n8n, Make or Zapier. |

Where things live:

```text
.
├── README.md
├── LICENSE
├── .gitignore
├── flagships/                 Multi-workflow systems, one folder per prefix
│   ├── outreach-agent/        OA: 8 n8n workflows, setup guide, sheet template, validator
│   ├── support-agent/         SA: design (planned)
│   └── crm-pipeline/          CRM: design (planned)
├── workflows/                 Single automations 01–14 (unchanged folders)
│   ├── 01-razorpay-zoho-books-invoicing/
│   ├── …
│   └── 14-content-repurposing/
├── docs/
│   ├── engineering-standards.md
│   └── importing.md
└── templates/
    └── workflow-README-template.md
```

Each single-automation folder holds a spec (`README.md`) and a `sample-data/` directory of fictional payloads. The export and a canvas screenshot are added when that workflow is built. `Shared` utilities live in my n8n account; their exports will go in a `shared/` folder when I add them.

## Flagship systems

### OA: Outreach Agent (n8n)

**Business outcome:** cold outreach that runs every day without becoming a full-time job. I built it so every prospect gets a first email based on research of their own website, and nothing goes out until I approve it. Follow-ups always happen. A reply stops the sequence. Unsubscribes and bounces are suppressed automatically. The same prospect can never be added twice, and every decision is logged.

**How it works.** Eight n8n workflows share one Google Sheet, which acts as the CRM. The status column is the queue between them.

| Workflow | What it does |
| --- | --- |
| OA-00 · Form Intake | A simple form to add one prospect by hand. It passes the prospect to OA-01. |
| OA-01 · Outreach Intake | Takes prospects from the form, a secured webhook, or rows pasted into the sheet. It cleans and validates them, removes duplicates by email and by domain, checks the suppression list, and logs every decision to an Events tab. |
| OA-02 · Research & Draft | Fetches each prospect's website. A Gemini agent judges fit and writes a short personal email, and a quality score gates weak drafts. If the website or the AI step fails, the row is marked `research_failed` and written to Errors. |
| OA-03 · Approval & Send | Sends me each draft in Gmail to approve, edit or reject. Approved emails go out only inside the prospect's business hours, under a daily cap, and after a last suppression check. |
| OA-04 · Follow-ups | Sends up to two short follow-ups in the same Gmail thread, and stops the moment the prospect replies. |
| OA-05 · Inbox Agent | Reads replies and sorts them: interested, question, objection, not now, unsubscribe, out of office or bounce. It suggests a reply for me to approve, or handles the reply itself (suppress, snooze, reschedule). |
| OA-06 · Weekly Report | Emails me a Monday summary: sent, replies, reply rate and bounces, plus a short AI insight. |
| OA-99 · Error Handler | Any failure in OA-00 to OA-06 sends me an alert email and adds a row to the Errors tab. |

**Where this is used:** I ran outreach and candidate pipelines by hand as Outreach Manager at DataisGood and at Careernet. OA is how I'd run that work now: the research and drafts are automatic, I approve every email, and no follow-up is missed.

**Skills shown:** n8n multi-workflow design, AI agents with tools and structured output (Gemini), web research, human-in-the-loop approval in Gmail, dedupe and suppression logic, timezone-aware send windows, rate caps, retries, a central error workflow, secret-checked webhooks that fail closed, an audit log, and an offline validator for the workflow JSON.

**Status:** ✅ Built. OA-00 through OA-06 were live-tested end to end on self-hosted n8n 2.8.4 (4–5 Nov 2026) and passed. Still untested: the OA-99 alert email, the webhook intake, and OA-04 follow-up 2 → no_response.

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

→ [flagships/outreach-agent/](flagships/outreach-agent/)

### SA: Support Agent (n8n)

**Business outcome:** routine support emails get a fast, correct answer, and the tricky ones reach a person with the context already gathered. The AI answers only from your own help docs. When it isn't sure, it hands the email over instead of guessing.

**How it works (planned design).** New support emails are triaged by an AI classifier: question, billing, bug, urgent or spam. Answers are drafted from your knowledge base, and low-risk replies can go out after approval. Anything sensitive, urgent or weakly matched is escalated to a person with a summary. Every ticket is logged with its category and outcome.

**Where this is used:** I built Ray, the AI career companion chatbot inside JobRays, so I've already shipped an AI assistant that answers users in a live product. SA brings that to a support inbox, answering only from your own docs.

**Skills shown:** AI triage with a fixed schema, retrieval from your docs (RAG), confidence-based escalation, human approval, and an outcome log.

**Status:** 🗺️ Planned. → [flagships/support-agent/](flagships/support-agent/)

### CRM: CRM Pipeline (Make + HubSpot)

**Business outcome:** every new lead becomes one clean HubSpot contact and deal, with an owner and a next task, so no lead sits untouched and no contact is duplicated.

**How it works (planned design).** Leads come in from forms and email. Make finds the existing contact in HubSpot or creates one. It qualifies the lead, creates the deal at the right stage, assigns an owner and adds a follow-up task. Stage changes trigger the next step, and a weekly pipeline summary goes to the owner.

**Where this is used:** A scenario: a B2B services team that gets leads from web forms and WhatsApp. Every lead lands in HubSpot as one deal with an owner and a next task, so nobody has to chase the spreadsheet. It builds on singles [09](workflows/09-form-lead-enrichment/) and [10](workflows/10-whatsapp-lead-qualifier/).

**Skills shown:** Make scenario design, HubSpot data modelling (contacts, deals, stages, tasks), dedupe, routing rules, error routes, and reporting.

**Status:** 🗺️ Planned. → [flagships/crm-pipeline/](flagships/crm-pipeline/)

## Single automations

| No. | Tool | What it does for the client | Status | Link |
| --- | --- | --- | --- | --- |
| 01 | n8n | Each captured Razorpay payment becomes a Zoho Books invoice that's emailed to the customer, and the owner gets an alert. No retyping. A fuller version runs at JobRays. | ✅ Built | [01](workflows/01-razorpay-zoho-books-invoicing/) |
| 02 | n8n | Scores every form lead with AI and logs it to a sheet. Hot leads alert the owner right away, and everyone else gets a thank-you with next steps. | ✅ Built (v1) | [02](workflows/02-ai-email-triage-crm/) |
| 03 | n8n | Answers support questions from your own docs only, and hands anything uncertain to a teammate in Slack. | 🗺️ Planned | [03](workflows/03-rag-support-agent/) |
| 04 | n8n | Each paid Stripe Checkout becomes one QuickBooks invoice and one receipt, with no duplicates on retries. | 🗺️ Planned | [04](workflows/04-stripe-quickbooks-invoicing/) |
| 05 | n8n | Starts a polite recovery sequence when a payment fails, so less revenue slips away unnoticed. | 🗺️ Planned | [05](workflows/05-failed-payment-recovery/) |
| 06 | n8n | Turns a call transcript into a short Zoho CRM note, and creates tasks only for what was actually agreed. | 🗺️ Planned | [06](workflows/06-meeting-notes-crm/) |
| 07 | n8n | Sends every workflow failure to one Slack channel, plus a weekday digest, so you hear about problems before customers do. | 🗺️ Planned | [07](workflows/07-ops-monitoring/) |
| 08 | n8n | Turns each finished voice-AI call into a HubSpot contact, with a follow-up task when the caller asked for one. | 🗺️ Planned | [08](workflows/08-voice-ai-agent-crm/) |
| 09 | Make | Every morning, finds leads in the sheet that haven't heard back in 2+ days, emails them, and records the follow-up. | ✅ Built (v1) | [09](workflows/09-form-lead-enrichment/) |
| 10 | Make | Qualifies WhatsApp enquiries with three questions, saves each one in HubSpot, and sends good leads your booking link. | 🗺️ Planned | [10](workflows/10-whatsapp-lead-qualifier/) |
| 11 | Make | Reads vendor bills from email, asks for your one-click approval in Slack, then books them in QuickBooks or Xero. | 🗺️ Planned | [11](workflows/11-accounts-payable-automation/) |
| 12 | Make | Sets up a new hire's Google Workspace account, ClickUp checklist and welcome email, then reminds the manager until the checklist is done. | 🗺️ Planned | [12](workflows/12-hr-onboarding/) |
| 13 | Zapier | Tags each customer in Mailchimp from their payment (`high-value`, `paid-customer` or `payment-failed`) without creating duplicate contacts. | ✅ Built (v1) | [13](workflows/13-stripe-mailchimp-lifecycle/) |
| 14 | Zapier | Turns a published article into LinkedIn and X drafts that wait in Notion for your approval in Slack. | 🗺️ Planned | [14](workflows/14-content-repurposing/) |

**Status key:** ✅ Built means it runs on the platform. 🧪 means built, with testing in progress. 🗺️ Planned means a full design spec (flow, failure cases and test checklist), with the build still to come. I add exports and screenshots to each folder as they're ready.

## Skills and stack

### Your stack, not mine

I work on n8n (including its AI agent nodes), Make, and Zapier, with Stripe, HubSpot, QuickBooks, Xero, Slack, Gmail, Google Sheets, Mailchimp, Notion, ClickUp, WhatsApp Business, OpenAI, Google Gemini, and Claude. For clients in India and the GCC, I also connect Razorpay and Zoho. Where a Zap should start from an HTTP payload, I use Webhooks by Zapier.

### How every workflow is built

I build every workflow to the same standard, so your team can trust it on a busy day. The full rules, naming, tables, and test checklist are in [docs/engineering-standards.md](docs/engineering-standards.md).

- Signed webhooks are verified before any write. App triggers that have no signature use the client's connection, or a shared secret that fails closed.
- A stable ID or dedupe check stops a second invoice, lead, task, or email.
- Transient API failures retry with backoff. Permanent errors stop and alert me.
- Every run and decision is logged, so there's an audit trail.
- AI steps use a fixed output schema, and a person approves the risky ones.
- Credentials live in n8n, Make, or Zapier. Sample files use placeholders and fictional payloads.
- Each folder ships with a test checklist that I run before anything goes live.

To import a workflow into your own account, see [docs/importing.md](docs/importing.md).

## Contact

I'm Raghav Deora, based in Prayagraj, India. If one of these workflows sounds like your week, I'd love to hear how you handle it today.

- GitHub: <https://github.com/Raghavdeora27>
- 📅 Book a call: <https://calendar.app.google/xPLZuaDusXaS93v17>
