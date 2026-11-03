# CRM = CRM Pipeline

**CRM (CRM Pipeline)** is my planned flagship system on Make and HubSpot. It takes every new lead through to a deal, so each lead becomes one clean contact with an owner, a stage and a next step.

**Status:** 🗺️ Planned. This folder holds the design. I'll add the Make blueprints (named CRM-00, CRM-01, …), the setup guide and a test log once it's built and tested.

## What you'll get (the instant value)

- **No lead left untouched.** Every new lead gets an owner and a follow-up task the moment it arrives.
- **No duplicate contacts.** Leads are matched to existing HubSpot contacts and companies before anything is created.
- **A pipeline you can trust.** Deals are created at the right stage, and the next step is triggered when the stage changes.
- **Less admin.** Nobody copies form or email leads into HubSpot by hand.
- **Visibility.** A weekly pipeline summary goes to the owner, and every action is logged.

## Where this is used

A scenario: a B2B services team that gets leads from web forms and WhatsApp. Every lead lands in HubSpot as one deal with an owner and a next task, so nobody has to chase a spreadsheet. It builds on singles [09](../../workflows/09-form-lead-enrichment/) and [10](../../workflows/10-whatsapp-lead-qualifier/).

## How it will work, step by step

| Step | What happens | Skills involved |
| --- | --- | --- |
| 1. Intake | Leads arrive from web forms, email and other sources into one Make scenario, with a shared secret checked on webhooks. | Make webhooks, multi-source intake |
| 2. Dedupe | Make searches HubSpot by email and by company domain, then updates the contact if it exists or creates it if not. | HubSpot search and upsert, dedupe logic |
| 3. Qualify | Rules (and optionally AI) score the lead and set the lifecycle stage. | Routing rules, AI scoring |
| 4. Create the deal | A deal is created in the right pipeline and stage, linked to the contact and company. | HubSpot data model: contacts, companies, deals, associations |
| 5. Assign | The deal gets an owner by rule and a follow-up task with a due date, and the owner is notified. | Assignment rules, task automation |
| 6. Move forward | Stage changes trigger the next step: a follow-up email, a reminder, or a handoff. | Event-driven scenarios |
| 7. Report and log | A weekly pipeline summary is sent, and every action is logged. Errors take an error route and alert me. | Reporting, error routes, retries |

**Related:** single automations [09, sheet lead follow-up](../../workflows/09-form-lead-enrichment/) and [10, WhatsApp lead qualifier](../../workflows/10-whatsapp-lead-qualifier/) cover smaller parts of this flow.
