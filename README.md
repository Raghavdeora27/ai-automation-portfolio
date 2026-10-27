# AI Automation Portfolio

Hi, I'm Raghav Deora. I build AI products and automations that take repetitive work off your team's plate: invoicing, lead follow-up, support replies, approvals, and onboarding. You get the hours back. Invoices go out the moment a payment lands, leads stop slipping through the cracks, retyping errors disappear, and a person still signs off on the decisions that matter.

### I built this for my own business first

I founded [JobRays](https://jobrays.io), an AI career companion that turns a long-term career goal into a daily plan someone can actually follow. Under the hood, it's a set of connected AI engines that work as one system:

- **Personalised plans.** Engines that map a user's goal into the job roles to target, the skills, courses, and projects for each milestone, and the full journey from today to the goal.
- **Daily progress tracking.** A tracker that logs what each user does every day and feeds it back, so every plan adjusts to real progress instead of going stale.
- **Ray, the AI companion.** A chat assistant that knows each user's plan and progress, and routes each task across OpenAI, Gemini, and Claude to balance quality and cost.
- **The business machinery.** Razorpay payments that become GST invoices in Zoho Books (including international transactions), transactional emails through Resend, and lifecycle journeys in Loops triggered by what users actually do.

I built the product (Next.js, FastAPI, and Supabase on Vercel) and every integration around it. So when I build a workflow for you, it's the same kind of system I trust with my own users and revenue.

### Process first, then automation

Before JobRays, I spent years in operations. As Operations Manager at BlueBox, I used Lean Six Sigma to cut process variability by 25% before we automated anything. As a consultant at Careernet, I guided 6,000+ candidates from interview to onboarding. I'm Lean Six Sigma certified, and I always fix the process before I automate it, because automating a messy handoff just delivers the mess faster.

### Built for a real week, not a demo

A slow API gets retried. A stored ID stops a second invoice, lead, or email from going out. A person approves the steps that should stay human. If something fails, you hear about it before your customer does.

### Your stack, not mine

I work on n8n, Make, and Zapier, with Stripe, HubSpot, QuickBooks, Xero, Slack, Gmail, OpenAI, and Claude. For clients in India and the GCC, I also connect Razorpay and Zoho.

**What you'll find here:** 14 workflow designs, each with the business problem, the flow, the error handling, and sample data. I add the working export and a demo video as each one is built and tested.

📅 [Book a call](https://calendar.app.google/xPLZuaDusXaS93v17) to talk through your workflow.

## Catalog

Fourteen workflows, grouped by platform. Pick the one that takes a job off your plate.

### n8n

| # | Workflow | Platform | Tools | Business problem | Status |
| --- | --- | --- | --- | --- | --- |
| 01 | [Razorpay payment to Zoho Books GST invoice and Resend receipt](workflows/01-razorpay-zoho-books-invoicing/) | n8n | Razorpay, Zoho Books, Resend | A captured payment should produce one GST invoice and one receipt email. | 🚧 In progress |
| 02 | [AI email triage to CRM](workflows/02-ai-email-triage-crm/) | n8n | Gmail, OpenAI, HubSpot, Slack | Inbound Gmail should be classified, filed on the HubSpot contact, and surfaced in Slack when a lead is ready to talk. | 🚧 In progress |
| 03 | [RAG support agent](workflows/03-rag-support-agent/) | n8n | Supabase pgvector, OpenAI or Claude, Slack | Support answers should come from company documents, with a person taking over in Slack when the docs are not enough. | 🚧 In progress |
| 04 | [Stripe payment to QuickBooks invoice and Resend receipt](workflows/04-stripe-quickbooks-invoicing/) | n8n | Stripe, QuickBooks Online, Resend | A paid Stripe Checkout should produce one QuickBooks invoice and one receipt email. | 🚧 In progress |
| 05 | [Failed-payment recovery](workflows/05-failed-payment-recovery/) | n8n | Stripe, Resend | A failed Stripe invoice should start a short dunning sequence that stops as soon as the invoice is paid. | 🚧 In progress |
| 06 | [Meeting notes to CRM](workflows/06-meeting-notes-crm/) | n8n | OpenAI, Zoho CRM | A call transcript should become a Zoho CRM note and a task only where the transcript states an action. | 🚧 In progress |
| 07 | [Ops monitoring](workflows/07-ops-monitoring/) | n8n | Slack, Supabase | Every workflow should report failures to Slack, with the run history stored in Supabase. | 🚧 In progress |
| 08 | [Voice AI agent to CRM](workflows/08-voice-ai-agent-crm/) | n8n | VAPI, OpenAI, HubSpot | A finished voice call should become a HubSpot contact and a follow-up task when the caller asked for one. | 🚧 In progress |

### Make

| # | Workflow | Platform | Tools | Business problem | Status |
| --- | --- | --- | --- | --- | --- |
| 09 | [Form lead to AI enrichment and scoring](workflows/09-form-lead-enrichment/) | Make | Typeform or Tally, OpenAI, HubSpot, Slack | A form lead should be enriched, scored, saved to HubSpot, and sent to the owner in Slack when the score is high enough. | 🚧 In progress |
| 10 | [WhatsApp lead qualifier](workflows/10-whatsapp-lead-qualifier/) | Make | WhatsApp Business Cloud API, OpenAI, HubSpot | A WhatsApp enquiry should answer a few qualifying questions, get a score, and land in HubSpot. | 🚧 In progress |
| 11 | [Accounts payable with human approval](workflows/11-accounts-payable-automation/) | Make | OpenAI, QuickBooks or Xero, Slack | A vendor bill received by email should wait for Slack approval before it is created in QuickBooks or Xero. | 🚧 In progress |
| 12 | [HR onboarding](workflows/12-hr-onboarding/) | Make | Google Workspace, ClickUp | A new-hire form should open the Workspace account and the ClickUp checklist, then remind the manager until the checklist is done. | 🚧 In progress |

### Zapier

| # | Workflow | Platform | Tools | Business problem | Status |
| --- | --- | --- | --- | --- | --- |
| 13 | [Lifecycle email engine](workflows/13-lifecycle-email-engine/) | Zapier | Stripe, Loops | Stripe subscription events should update Loops so the right lifecycle email can send. | 🚧 In progress |
| 14 | [Content repurposing](workflows/14-content-repurposing/) | Zapier | OpenAI, Notion, Slack | A blog URL should become drafts stored in Notion that wait for Slack approval. | 🚧 In progress |

## How every workflow is built

I build every workflow to the same standard, so your team can trust it on a busy day. The full rules, tables, and test checklist are in [docs/engineering-standards.md](docs/engineering-standards.md).

- Signed webhooks are verified before any write. App triggers that have no signature use the client's connection, or a shared secret.
- A stable provider id is stored so a retry does not create a second invoice, lead, task, or email.
- Transient API failures retry with backoff. Permanent errors stop and alert.
- Exhausted failures go to [ops monitoring](workflows/07-ops-monitoring/) for a Slack alert. The run history is in Supabase.
- Credentials live in n8n, Make, or Zapier. Sample files use placeholders and fictional payloads. `dry_run` defaults to true.
- Each folder ships with a test checklist that I run before anything goes live.

## How to import a workflow

The exports are not in the folders yet. When a folder contains an export or a shared Zap link, import it as follows.

### n8n

1. Open the n8n instance.
2. Go to **Workflows**.
3. Choose **Import from File**.
4. Select the workflow JSON in that folder.
5. Reconnect each credential in the n8n credential store. Use the credential names in the workflow README.
6. Fill the config variables in that README, and leave `dry_run` on for the first test.
7. Run the folder's test checklist against `sample-data/` before activating the workflow.

### Make

1. Create a scenario, or open an empty one.
2. Open the scenario menu.
3. Choose **Import Blueprint**.
4. Select the blueprint JSON in that folder.
5. Map every module to a connection in the client's Make account.
6. Fill the scenario variables listed in the workflow README.
7. Run once with the sample payload before turning the scenario on.

### Zapier

Zapier does not import a JSON file the way n8n and Make do. Workflows 13 and 14 ship as a shared Zap link or a Zap template, or they are rebuilt from the folder README. No shared link is in those folders yet.

When a folder contains a shared link or a template URL:

1. Open the shared Zap link or the template URL named in that workflow's README.
2. Choose **Try this Zap** and select the client's Zapier account.
3. Reconnect each app. Use the credential names in the workflow README. Zapier stores the secrets in the client's connections.
4. Fill the input fields listed in that README, including the Storage by Zapier key prefix, and leave `dry_run` on for the first test.
5. Leave the Zap off until the folder's test checklist has been run against `sample-data/`.

When the folder has no shared link yet, rebuild the Zap from the README:

1. Create a Zap in the client's account and leave it off.
2. Set the trigger named in the README. For Stripe or Slack, use the native app trigger so the connection holds the signing secret. A Catch Hook rebuild has to verify the signature before any write.
3. Add each action in the flow order: the allowlist filter, the Storage by Zapier idempotency key, the app actions, and the ops webhook step on the error path.
4. Map fields from the sample payload in `sample-data/`.
5. Run a test with that sample and `dry_run` on. Turn the Zap on only after the checklist passes.

## Repository structure

```text
.
├── README.md
├── LICENSE
├── .gitignore
├── docs/
│   └── engineering-standards.md
├── templates/
│   └── workflow-README-template.md
└── workflows/
    ├── 01-razorpay-zoho-books-invoicing/
    ├── 02-ai-email-triage-crm/
    ├── 03-rag-support-agent/
    ├── 04-stripe-quickbooks-invoicing/
    ├── 05-failed-payment-recovery/
    ├── 06-meeting-notes-crm/
    ├── 07-ops-monitoring/
    ├── 08-voice-ai-agent-crm/
    ├── 09-form-lead-enrichment/
    ├── 10-whatsapp-lead-qualifier/
    ├── 11-accounts-payable-automation/
    ├── 12-hr-onboarding/
    ├── 13-lifecycle-email-engine/
    └── 14-content-repurposing/
```

Each workflow folder holds a design spec (`README.md`) and a `sample-data/` directory of fictional payloads. The workflow export and a canvas screenshot are added when that workflow is built.

## Contact

I'm Raghav Deora, based in Prayagraj, India. If one of these workflows sounds like your week, I'd love to hear how you handle it today.

- GitHub: <https://github.com/Raghavdeora27>
- 📅 Book a call: <https://calendar.app.google/xPLZuaDusXaS93v17>
