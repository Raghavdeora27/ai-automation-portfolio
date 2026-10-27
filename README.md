# AI Automation Portfolio

Production-style automation workflows by [Raghav Deora](https://github.com/Raghavdeora27), an AI automation developer based in Prayagraj, India.

Raghav builds workflows for payments, CRM, finance, support, and internal operations. The catalog runs on n8n, Make, and Zapier. Most of the workflows use the tools international clients already run: Stripe, HubSpot, QuickBooks, Xero, Slack, Gmail, and OpenAI, with Claude where a longer answer helps. Razorpay, Zoho Books, and Zoho CRM stay in the catalog for India and GCC work. He was previously an operations manager and has a Lean Six Sigma background, so each spec names the exception path as well as the happy path.

This repository is a public catalog of those designs for Upwork and direct freelance clients, and for technical reviewers. Every workflow below is **in progress**. Nothing has been built yet. A workflow ships either live on the client's sandbox or test-mode account, or in mock mode with the pinned fictional payloads in `sample-data/` and a `dry_run` flag. Each folder lists the credentials to plug in. Exports are added one folder at a time after the workflow is built and tested. Client names, performance numbers, and testimonials stay out of the repo until a client agrees to publish them.

Book a working session: <https://calendar.app.google/xPLZuaDusXaS93v17>

## Catalog

Fourteen workflows, grouped by platform. The tools column is what that workflow connects. Sandbox credentials are plugged in at handover. They are not stored in this repo.

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

Each design follows the same engineering bar. The full rules, tables, and test checklist are in [docs/engineering-standards.md](docs/engineering-standards.md).

- Signed webhooks are verified before any write. App triggers that have no signature use the client's connection, or a shared secret.
- A stable provider id is stored so a retry does not create a second invoice, lead, task, or email.
- Transient API failures retry with backoff. Permanent errors stop and alert.
- Exhausted failures go to [ops monitoring](workflows/07-ops-monitoring/) for a Slack alert. The run history is in Supabase.
- Credentials live in n8n, Make, or Zapier. Sample files use placeholders and fictional payloads. `dry_run` defaults to true.
- Each folder has a test checklist. The boxes in this repo have not been run, because the exports are not here yet.

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

Raghav Deora — Prayagraj, India.

- GitHub: <https://github.com/Raghavdeora27>
- Book a call: <https://calendar.app.google/xPLZuaDusXaS93v17>
