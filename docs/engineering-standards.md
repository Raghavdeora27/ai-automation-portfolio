# Engineering standards

Each workflow in this portfolio is specified to the rules below. A workflow stays **🚧 In progress** until its folder contains the export, a canvas screenshot, the fixtures used in a test, and a completed checklist. Nothing in this repository is marked past that line in advance.

n8n and Make are the platforms used in the catalog. A Zapier build for a client follows the same rules: a signed trigger where the app provides one, a stored idempotency key, capped retries, and a call to the ops monitoring workflow when a run fails.

## Webhook signature verification

A webhook that creates or updates a business record is verified before any write, send, or model call.

Razorpay signs the raw request body. The header is `X-Razorpay-Signature`. The check is HMAC-SHA256 of the exact bytes received, using the webhook secret. Re-serializing the JSON object changes the digest, so the verifier uses the raw body. A missing, stale, or mismatched signature ends the run with HTTP 401. The run writes nothing and sends nothing.

Form tools and some app triggers do not sign requests. Those workflows require a shared secret in a header and compare it in constant time. A missing secret ends the run the same way.

In n8n the Webhook node is set to expose the raw body, and the next node performs the check. In Make the check is the first module on the scenario. The webhook secret is stored as a credential. Logs record `signature_valid: false`. They do not record the header or the computed digest.

## Idempotency and deduplication

Providers retry webhooks. Operators click twice. Every workflow that writes to a second system uses an idempotency key:

```text
{workflow}:{entity}:{provider_id}:{step}
```

The step is part of the key so a completed invoice is not created again when only the receipt email failed. Example: `01-razorpay-zoho-books-invoicing:payment:pay_MockCaptured0001:invoice`.

The system of record for n8n workflows is a Supabase table, `processed_events`. Make scenarios use a Make data store with the same columns, unless the client asks for one shared Supabase table. This is a design sketch. The table has not been created in a client project by this repo.

| Column | Purpose |
| --- | --- |
| `idempotency_key` | Primary key. |
| `workflow` | Folder name, such as `01-razorpay-zoho-books-invoicing`. |
| `status` | `in_progress`, `completed`, or `failed`. |
| `step` | Last step that succeeded, so a replay can resume. |
| `correlation_id` | Provider id an operator can search for. |
| `result_ref` | Downstream id, such as a Zoho invoice id. |
| `last_error` | Short error code from the last failure. |
| `updated_at` | Used to decide whether an `in_progress` row is stale. |

A new delivery inserts a row with status `in_progress`. The unique key decides the rest:

| Existing row | What the run does |
| --- | --- |
| None | Insert `in_progress` and continue. |
| `completed` | Stop and return success to the provider. |
| `failed` | Resume from the recorded step. |
| `in_progress` and younger than 15 minutes | Stop. Another run owns the key. |
| `in_progress` and older than 15 minutes | Resume from the recorded step. |

The 15 minute window is config (`idempotency_stale_minutes`). A run marks the row `completed` only after the side effect for that step has succeeded. A validation failure marks it `failed` and alerts. It does not mark the step completed.

## Retries with backoff

Retries are for transient failures: network errors, timeouts, and HTTP 408, 429, 500, 502, 503, and 504. HTTP 400, 401, 403, 404, and 422 are permanent: the run stops and alerts. An HTTP 409 on the idempotency insert is the dedupe case above, not a provider failure.

Defaults, all configurable:

- Cap: 5 attempts.
- Delays: 30 seconds, 2 minutes, 8 minutes, 30 minutes, 2 hours.
- Jitter: up to 20 percent of the delay.
- When the provider sends `Retry-After`, that value replaces the default delay for that attempt.

n8n workflows use an explicit retry counter and a Wait node so the attempt number is logged. Make scenarios use a Break error handler with exponential backoff and the same cap. A permanent failure leaves the idempotency row at `failed`.

## Central error workflow

[Workflow 12, ops monitoring](../workflows/12-ops-monitoring/), is the error workflow for the catalog.

Every workflow sends a normalized event when a run fails, and a short run event when a run finishes. Make cannot use n8n's internal error trigger, so both platforms POST to the ops webhook. n8n workflows also set workflow 12 as their Error Workflow, which catches a crash that never reaches the HTTP node.

The ops webhook checks a shared secret header, `X-Ops-Token`, with the same rules as any other webhook. The token lives in the credential store.

```json
{
  "kind": "error",
  "workflow": "01-razorpay-zoho-books-invoicing",
  "execution_id": "exec_mock_0001",
  "node": "Zoho Books create invoice",
  "correlation_id": "pay_MockCaptured0001",
  "step": "invoice",
  "outcome": "failed",
  "error_code": "zoho_books_429",
  "message": "Zoho Books returned 429 after 5 attempts.",
  "occurred_at": "2026-10-15T10:00:00Z"
}
```

The alert names the workflow, execution id, node, correlation id, error code, and message. It posts to the Slack channel in `alert_channel`. If Slack returns an error, the same text goes to `alert_email`. Repeats of the same workflow, node, and error code inside 30 minutes collapse into one message with a count. The window is config (`alert_dedupe_minutes`).

Workflow 12 does not call itself. If both Slack and email fail, the failed execution remains in the n8n execution list. The log row remains if it was written before the alert failed.

## Structured logging

Each workflow writes one log row per step to Supabase table `workflow_logs`. This is a design sketch. The table has not been created by this repo.

| Field | Content |
| --- | --- |
| `ts` | ISO-8601 time. |
| `workflow` | Folder name. |
| `execution_id` | n8n execution id or Make run id. |
| `correlation_id` | Provider id for the business record. |
| `step` | Short step name. |
| `outcome` | `ok`, `retry`, `failed`, or `skipped`. |
| `duration_ms` | Time spent in the step. |
| `provider_status` | HTTP status, when there is one. |
| `error_code` | Empty on success. |

The correlation id is a provider id such as a payment id or a message id. Message bodies, webhook signatures, authorization headers, and document text stay out of the log. The CRM or the source system keeps the full record.

## Credentials

API keys, OAuth tokens, webhook secrets, and service-role keys live in the n8n credential store or in Make connections. The workflow export stores the credential name and a reference. It does not store the secret value.

Before an export is committed, search the file for live secrets: `sk-`, `sk_live`, `rzp_live`, `rzp_test_` followed by a secret, `Bearer `, `xoxb-`, private-key blocks, and webhook secrets. Sample data in this repo uses fictional ids, `example.com` addresses, and the signature string `mock_signature_not_valid`.

Each workflow README lists the credential names the client creates. The values are filled in during handover, in the client's own account.

## Environment-specific config

Environment-specific values sit in one config step at the top of the workflow (an n8n Set node, or Make scenario variables). They are not copied into Code nodes.

Typical keys:

| Variable | Purpose |
| --- | --- |
| `dry_run` | When true, the run writes only to test records and skips customer-facing sends. The intended payload is written to the log. |
| `alert_channel` | Slack channel id for this environment. |
| `alert_email` | Backup inbox for this environment. |
| `zoho_organization_id` | Zoho Books organization. Use the client's test organization while `dry_run` is on. |
| `from_address` | Verified sender for Resend or the email connection. |
| Business thresholds | Tax rate, score cutoffs, reminder delays, model routing cutoffs. |

Dev and production use different channels, organizations, and sender addresses. The first test of a workflow runs with `dry_run` true.

## Rate limits

| Source | What goes wrong | Specified handling |
| --- | --- | --- |
| Razorpay webhooks | Razorpay retries when the receiver is slow, which creates a second delivery. | Return HTTP 200 after the signature check and the idempotency insert. Continue the business steps after the response. |
| Zoho Books and Zoho CRM | The organization rate limit returns 429. | One write at a time per organization. Back off on 429. Honor `Retry-After`. |
| OpenAI, Claude, Gemini | Quota, rate limit, or a runaway loop. | Cap model retries at 3. Set a max token budget on the node. A workflow does not send model output back into the same model in a loop. |
| Resend and WhatsApp | A burst of sends trips the provider limit or the WhatsApp quality rating. | Send sequentially. Inside the 24 hour WhatsApp session window, send a session message. Outside it, send a pre-approved template. |
| Slack | One message per run becomes noise. | Failures alert immediately, with the 30 minute collapse above. The daily digest is a single message. |

## Test data and a test checklist

`sample-data/` in each workflow folder holds fictional payloads for design review. Addresses use `example.com`. Payment ids, GSTINs, and phone numbers are made up. These files are not a completed test suite, and they are not records from a client.

Inbound email, PDFs, chat messages, and transcripts are untrusted data. Classification and extraction use a fixed schema. Text inside that content is not a workflow instruction. The test checklist includes one fixture that asks the model to change its category or ignore its rules.

Shared checklist, to be copied into the run notes when a workflow is tested. None of these boxes have been executed for this repository.

- [ ] An invalid signature or shared secret produces no write and no customer message.
- [ ] The happy-path fixture completes with `dry_run` true.
- [ ] A second delivery of the same provider id does not create a second business record.
- [ ] A forced HTTP 503 is retried, then succeeds, and the log shows the attempt count.
- [ ] A forced HTTP 400 alerts once and is not retried.
- [ ] A missing required field alerts and the run does not fill in a guess.
- [ ] Log rows contain the correlation id and contain no credential, signature, or raw body.
- [ ] The exported JSON contains no secret values.
- [ ] A test with `dry_run` false was run only against the client's test account.
- [ ] A fixture with an instruction hidden in the content still follows the schema.

Workflow READMEs add the cases that are specific to that flow. Those boxes have not been executed either.

## Handover

The workflow README is the handover document. It states the business problem, trigger, flow, diagram, error handling, credential names, config variables, and test checklist.

When a workflow leaves **In progress**, the folder also contains:

- The n8n export or Make blueprint.
- A screenshot of the canvas.
- The fixtures used in the test, and the completed checklist.
- The list of credential names the client has connected.
- The config values the client still has to confirm, including tax, routing, and sender address.

Handover includes a short walkthrough of the failure path: how an alert looks, where the execution id is, and which client operator responds. That walkthrough is done with the client at handover. This repository does not record one.
