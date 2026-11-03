# SA = Support Agent

**SA (Support Agent)** is my planned flagship n8n system for support email. AI triages the inbox, answers routine questions from your own docs, and escalates everything else to a person with the context already gathered.

**Status:** 🗺️ Planned. This folder holds the design. I'll add the workflows (named SA-00, SA-01, … like the OA system), the setup guide and a test log once it's built and tested.

## What you'll get (the instant value)

- **Routine questions answered fast**, using only your help docs and policies, never a guess.
- **Nothing important buried.** Urgent, billing and angry emails are flagged and routed to the right person first.
- **Clean handovers.** When the AI isn't confident, a person gets the email with a summary, the closest doc matches and a suggested reply.
- **You stay in control.** Replies go out only after approval, and per category you choose what (if anything) may send on its own.
- **An audit trail.** Every ticket is logged with its category, the answer source, who approved it and the outcome.

## Where this is used

I built Ray, the AI career companion chatbot inside JobRays, so I've already shipped an AI assistant that answers users in a live product. SA brings that to a support inbox. Routine questions get an answer from your own docs on day one, and anything unclear goes to a person. Single [03](../../workflows/03-rag-support-agent/) is its first building block.

## How it will work, step by step

| Step | What happens | Skills involved |
| --- | --- | --- |
| 1. Intake | New emails reach the support inbox through a Gmail trigger, or a form or webhook. The sender and thread are matched to any earlier ticket. | Multi-channel intake, thread matching, dedupe |
| 2. Triage | An AI classifier with a fixed schema sets the category (question, billing, bug, urgent, spam), the priority and the sentiment. Text inside the email is treated as data, never as instructions. | AI classification, structured output, prompt-injection safety |
| 3. Answer | For questions, the agent searches your knowledge base and drafts a reply that cites the docs it used. | Retrieval (RAG), AI agent with tools |
| 4. Confidence gate | A weak match, a sensitive topic or a missing source sends the email to escalation instead of an answer. | Guardrails, confidence thresholds |
| 5. Approve or escalate | A person approves or edits the draft, or takes over an escalated ticket that arrives with a summary. | Human-in-the-loop, routing |
| 6. Log and report | Every ticket and outcome is logged, and a weekly summary shows volumes, categories and escalations. | Outcome logging, reporting |
| 7. Errors | Failures go to an error workflow and alert me. | Central error handling, retries |

**Related:** single automation [03, RAG support agent](../../workflows/03-rag-support-agent/) is the answering core. SA wraps it with triage, escalation and reporting.
