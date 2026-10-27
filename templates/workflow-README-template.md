# NN — Workflow name

Author note, delete after copying: point the standards link at `../../docs/engineering-standards.md`. The link below is correct for `templates/`.

**Platform:** n8n, Make, or Zapier
**Status:** 🚧 In progress

The design is documented here. I add the working export and a demo video as soon as this workflow is built and tested.

Standards: [../docs/engineering-standards.md](../docs/engineering-standards.md)

## For you

**[One line naming the outcome.]**
[One or two sentences naming the pain.]

- [Outcome.]
- [Outcome.]
- [Outcome.]

**Who it's for:** [the team or business.]
**Tools:** [plain names], on n8n, Make, or Zapier.

## Business problem

The precise behavior, in the present tense. Leave client names, volumes, and timings out unless the client has published them. Do not write "when this workflow is built."

## Trigger

The event, the system that emits it, and the credential or secret used to accept it.

## Flow

1. Verify the request.
2. Insert or resume the idempotency key.
3. Do the business steps, in order. Name the system each step writes to.
4. Mark the key completed only after the side effect succeeds.
5. On exhausted or permanent failure, POST the ops event to workflow 07.

## Architecture

```mermaid
flowchart TD
  trigger["Trigger"] --> verify["Verify signature or shared secret"]
  verify -->|invalid| reject["Return 401 and stop"]
  verify -->|valid| dedupe["Insert idempotency key"]
  dedupe -->|already completed| ack["Return success and stop"]
  dedupe -->|new or resumable| work["Business steps"]
  work --> complete["Mark key completed"]
  work -->|transient failure| retry["Retry with backoff"]
  retry -->|attempts exhausted| alert["Ops monitoring alert"]
  work -->|permanent failure| alert
```

## Error handling and edge cases

List the cases that would double-write, notify the wrong person, or guess a missing field. For each case, state the specified behavior.

Retries, backoff, and the ops payload follow [the engineering standards](../docs/engineering-standards.md).

## Integrations and credentials

Secrets live in the platform credential store. The export holds credential names only.

| System | Credential name | Used for |
| --- | --- | --- |
| Example | `example_credential` | What this connection does |

### Config

| Variable | Purpose | Spec default |
| --- | --- | --- |
| `dry_run` | Skip customer-facing sends and write the intended payload to the log. | `true` |

## Test checklist

I run these before anything goes live. Also complete the shared checklist in [the engineering standards](../docs/engineering-standards.md).

- [ ] Happy-path fixture completes in `dry_run`.
- [ ] Duplicate delivery does not double-write.
- [ ] The workflow-specific edge case below behaves as written.

## Files

Not in this folder yet:

- Workflow export (n8n JSON, a Make blueprint, or a Zapier shared Zap link).
- Screenshot of the canvas.
- The fixture set captured during a real test run.

`sample-data/` holds fictional payloads for design review. They are not a completed test suite.

| Path | What it is |
| --- | --- |
| `sample-data/example.json` | Fictional input. |
