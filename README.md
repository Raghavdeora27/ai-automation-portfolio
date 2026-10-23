# AI Automation Portfolio

Production-style automation workflows by [Raghav Deora](https://github.com/Raghavdeora27), an AI automation developer based in Prayagraj, India.

Raghav builds workflows for payments, CRM, finance, support, and internal operations. He works in n8n, Make, and Zapier, and connects OpenAI, Claude, and Gemini with Zoho CRM, Zoho Books, Razorpay, Resend, Loops, Next.js, and Supabase. He was previously an operations manager and has a Lean Six Sigma background, so each spec names the exception path as well as the happy path.

This repository is a public catalog of those designs for Upwork and direct freelance clients, and for technical reviewers. Every workflow below is **in progress**. Exports are added one folder at a time after the workflow is built and tested. Client names, performance numbers, and testimonials stay out of the repo until a client agrees to publish them.

Book a working session: <https://calendar.app.google/xPLZuaDusXaS93v17>

## Catalog

| # | Workflow | Platform | Business problem | Key integrations | Status |
| --- | --- | --- | --- | --- | --- |
| 01 | [Razorpay payment to Zoho Books GST invoice and Resend receipt](workflows/01-razorpay-zoho-books-invoicing/) | n8n | A captured payment should produce one GST invoice and one receipt email. | Razorpay, Zoho Books, Resend | 🚧 In progress |
| 02 | [AI email triage to Zoho CRM](workflows/02-ai-email-triage-zoho-crm/) | n8n | Inbound mail should be classified, filed on the right CRM record, and surfaced when a lead is ready to talk. | OpenAI, Zoho CRM, Slack | 🚧 In progress |
| 03 | [WhatsApp lead qualifier](workflows/03-whatsapp-lead-qualifier/) | Make | A WhatsApp enquiry should answer a few qualifying questions, get a score, and land in the CRM or a sheet. | WhatsApp, OpenAI, Zoho CRM, Google Sheets | 🚧 In progress |
| 04 | [RAG support agent with model routing](workflows/04-rag-support-agent/) | n8n | Support answers should come from company documents, with a person taking over when the docs are not enough. | Supabase, OpenAI, Claude, Gemini, Slack | 🚧 In progress |
| 05 | [Failed-payment recovery](workflows/05-failed-payment-recovery/) | n8n | A failed payment should start a short dunning sequence that stops as soon as the customer pays. | Razorpay, Resend, WhatsApp, Zoho CRM | 🚧 In progress |
| 06 | [Loops lifecycle engine](workflows/06-loops-lifecycle-engine/) | n8n | Subscription events should update lifecycle properties and enter the right Loops segment. | OpenAI, Loops | 🚧 In progress |
| 07 | [Accounts-payable automation](workflows/07-accounts-payable-automation/) | n8n | A vendor bill received by email should become a Zoho Books draft and wait for a human approval before it is posted. | OpenAI, Zoho Books, Slack | 🚧 In progress |
| 08 | [HR onboarding](workflows/08-hr-onboarding/) | Make | A new-hire form should open the onboarding tasks, send the welcome email, and remind the manager until the checklist is done. | ClickUp, email | 🚧 In progress |
| 09 | [Lead enrichment and routing](workflows/09-lead-enrichment-routing/) | Make | A form lead should be enriched, scored, and assigned to an owner with a notification. | Zoho CRM, OpenAI, Slack | 🚧 In progress |
| 10 | [Meeting notes to CRM](workflows/10-meeting-notes-crm/) | n8n | A call transcript should become a CRM note and a task only where the transcript states an action. | OpenAI, Zoho CRM, ClickUp | 🚧 In progress |
| 11 | [Content repurposing agent](workflows/11-content-repurposing-agent/) | n8n | A blog URL should become LinkedIn and X drafts that wait in an approval queue. | OpenAI, Slack | 🚧 In progress |
| 12 | [Ops monitoring](workflows/12-ops-monitoring/) | n8n | Every workflow should report failures to one place, and an operator should get a daily digest. | Slack, email, Supabase | 🚧 In progress |

## How every workflow is built

Each design follows the same engineering bar. The full rules, tables, and test checklist are in [docs/engineering-standards.md](docs/engineering-standards.md).

- Signed webhooks are verified before any write.
- A stable provider id is stored so a retry does not create a second invoice, lead, task, or email.
- Transient API failures retry with backoff. Permanent errors stop and alert.
- Exhausted failures go to [ops monitoring](workflows/12-ops-monitoring/) for a Slack or email alert.
- Credentials live in n8n or Make. Sample files use placeholders and fictional payloads.
- Each folder has a test checklist. The boxes in this repo have not been run, because the exports are not here yet.

## How to import a workflow

The JSON exports are not in the folders yet. When a folder contains an export, import it as follows.

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
    ├── 02-ai-email-triage-zoho-crm/
    ├── 03-whatsapp-lead-qualifier/
    ├── 04-rag-support-agent/
    ├── 05-failed-payment-recovery/
    ├── 06-loops-lifecycle-engine/
    ├── 07-accounts-payable-automation/
    ├── 08-hr-onboarding/
    ├── 09-lead-enrichment-routing/
    ├── 10-meeting-notes-crm/
    ├── 11-content-repurposing-agent/
    └── 12-ops-monitoring/
```

Each workflow folder holds a design spec (`README.md`) and a `sample-data/` directory of fictional payloads. The workflow export and a canvas screenshot are added when that workflow is built.

## Contact

Raghav Deora — Prayagraj, India.

- GitHub: <https://github.com/Raghavdeora27>
- Book a call: <https://calendar.app.google/xPLZuaDusXaS93v17>
