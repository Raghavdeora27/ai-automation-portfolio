# OA (Outreach Agent): setup guide

This is a portfolio build for n8n 1.x and 2.x with the LangChain nodes. It uses Gemini, Google Sheets as the CRM, and Gmail.

Every workflow imports with **no credentials and no IDs**. You attach credentials, fill the placeholders (including two workflow-ID placeholders: OA-99's ID in every Settings → Error workflow, and OA-01's ID in OA-00's **Run OA-01 Intake** node), and test.

---

## 0. What's in the box

| Path | What it is |
|---|---|
| `workflows/OA-99-error-handler.json` | Error Trigger. Sends a Gmail alert to `ALERT_EMAIL` and adds a row to the **Errors** tab. **Import first.** |
| `workflows/OA-01-intake.json` | Webhook (secret header), Schedule (`new_import` rows) and **When Executed by Another Workflow** (called by OA-00, source `form`). Then normalise, validate, dedupe by email and domain, and check suppression. Result: status `new`. **Import second.** |
| `workflows/OA-00-form-intake.json` | The **n8n Form** (Add Prospect). Maps the fields and calls OA-01 by workflow ID (Execute Workflow, waits), then shows a Form Ending page saying whether the prospect was added. Split out because n8n refuses to run a Form-Trigger workflow that contains **Respond to Webhook** nodes (OA-01 needs them for the webhook API). **Import third, after pasting OA-01's ID.** |
| `workflows/OA-02-research-draft.json` | Every 30 min, 10 `new` rows. Fetches the site, then a Gemini agent with a structured parser and a Sheets tool writes a draft. Quality gate, then `drafted` or `disqualified`. |
| `workflows/OA-03-approval-send.json` | Lane A (every 5 min): Gmail send-and-wait approval (Approve / Approve with edits / Reject). Lane B (every 15 min): sends approved drafts inside the send window, within the cap, after a suppression re-check. |
| `workflows/OA-04-followups.json` | Hourly. A reply in the thread sets `replied`. Otherwise Gemini writes a 2–3 line follow-up in the same thread: `followup_1`, then `followup_2`, then `no_response`. |
| `workflows/OA-05-inbox-agent.json` | Gmail trigger. Matches the email to a prospect, then a Gemini classifier and a Switch route it by category: interested / question / objection / not_now / unsubscribe / out_of_office / bounce / other. |
| `workflows/OA-06-weekly-report.json` | Monday 09:00 (Asia/Kolkata). Metrics, a 3-line Gemini insight, and an HTML email. |
| `sheet-template/outreach-crm-template.xlsx` | The CRM workbook with 5 tabs and exact headers, plus a README tab. A CSV per tab is included too. |
| `sample-prospects.csv` | 8 fake test prospects: 6 valid, 1 duplicate email, 1 duplicate domain. |
| `validate_workflows.py` | An offline validator. It checks node types and versions, parameter names against the n8n node catalogue, connections, `$('Node')` references, retries, secrets, and JS syntax. |
| `generator/` | The Python that generates the JSONs. Optional. Use it to regenerate after a bulk change. |

---

## 1. Create the Google Sheet (5 min)

1. Open Google Drive and upload `sheet-template/outreach-crm-template.xlsx`. Choose **Open with Google Sheets**, then **File → Save as Google Sheets**.
   - Alternatively, create a blank sheet with tabs **Prospects, Messages, Events, Suppression, Errors** and paste each CSV header into row 1.
2. Tab names and headers must match **exactly**. The workflows match on the column names `prospect_id` and `message_key`.
3. Copy the sheet ID from the URL: `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`.
4. Import the test prospects. Open `sample-prospects.csv` and **replace every email with your own plus-address**, for example `you+asha@yourdomain.com` or `you+ben@yourdomain.com`. Then paste the rows under the Prospects header.
   - Keep `status = new_import`.
   - Keep the `  BEN@Example.ORG ` row as it is. It tests email dedupe, so after your swap make it the same address as Ben's with different case and spacing.
   - The `example.*` websites are fine. Gemini will mostly mark them **disqualified** (no real business), which is a good demo of the fit gate. For **drafts**, use any public small-business site; the 3 non-example sites (iana.org, info.cern.ch, w3.org) already fetch fine.
   - **Never** put a real third party's email in the sheet while testing.

## 2. Import order

In n8n, go to **Workflows → Import from File**:

1. **`OA-99-error-handler.json` first.** Open it and copy its workflow ID from the URL (`/workflow/<ID>`).
2. **`OA-01-intake.json` second.** Save it and copy **its** workflow ID from the URL (`/workflow/<ID>`).
3. **`OA-00-form-intake.json` third.** Open the **Run OA-01 Intake** node → *Workflow* → *By ID* and replace `REPLACE_WITH_OA01_INTAKE_WORKFLOW_ID` with OA-01's ID (or pick "OA-01 Outreach Intake" from the list). Alternatively, find-and-replace the placeholder in the JSON before importing.
4. Then import `OA-02`, `OA-03`, `OA-04`, `OA-05` and `OA-06`.
5. In each of OA-00–OA-06, go to **Settings → Error workflow** and select **"OA-99 Error Handler"**. The JSON carries the placeholder `REPLACE_WITH_OA99_ERROR_HANDLER_WORKFLOW_ID`; picking from the dropdown overwrites it.


> CLI alternative: `n8n import:workflow --input=workflows/OA-99-error-handler.json`, and so on. The bundle has been import-tested on n8n **1.123.92** and **2.45.7**.

## 3. Credentials (create once, then pick in every node)

| Credential | n8n type | Used by |
|---|---|---|
| Google Sheets | *Google Sheets OAuth2 API* | All Sheets nodes in OA-01–OA-06 and OA-99, plus the `prior_messages` tool in OA-02 (OA-00 has no Sheets nodes) |
| Gmail | *Gmail OAuth2 API* | OA-03 (approval and send), OA-04 (thread read and reply), OA-05 (trigger, mark read, approval, reply), OA-06 (report), OA-99 (alert) |
| Gemini | *Google Gemini (PaLM) API*, with a key from aistudio.google.com | Gemini Chat Model nodes in OA-02 (×2), OA-04, OA-05 and OA-06 |

Tips:
- Each node shows a red ⚠ until a credential is picked. Open each one: the credential dropdown auto-selects if you have only one.
- OA-00 needs **no** credentials. OA-01 needs only Sheets. OA-99 needs Gmail and Sheets.
- Model: `models/gemini-2.5-flash` is preset. You can change it in each "Gemini" sub-node.

## 4. Fill the Config node (in EVERY workflow)

Each workflow except OA-00 has exactly one **Config** (Set) node right after its trigger(s). Edit these values in all 7 (OA-01–OA-06 and OA-99; OA-00 has no Config, it only forwards the form to OA-01):

| Key | Example | Notes |
|---|---|---|
| `SHEET_ID` | `1AbC…xyz` | From step 1.3 |
| `SENDER_NAME` | `Raghav` | Signature in drafts |
| `SENDER_EMAIL` | `you@yourdomain.com` | The Gmail account the credential uses |
| `APPROVER_EMAIL` | your inbox | Receives approval forms |
| `ALERT_EMAIL` | your inbox | Receives errors from OA-99 |
| `DAILY_CAP` | `30` | Counts initial sends, follow-ups and replies per day |
| `DEFAULT_TIMEZONE` | `Asia/Kolkata` | Used when a prospect's timezone is blank or invalid |
| `SEND_WINDOW_START_HOUR` / `END_HOUR` | `9` / `17` | Mon–Fri in the prospect's timezone |
| `MY_SERVICE_ONE_LINER` | one sentence | What you offer; the AI uses it |
| `IGNORE_SEND_WINDOW` | `false` | **Test knob.** Set `true` to send outside 09–17 or at weekends |
| `TEST_FOLLOWUP_DELAY_MINUTES` | `0` | **Test knob.** For example, `5` makes follow-ups due 5 minutes after a send instead of 3 or 4 business days |

OA-02 also has `BATCH_SIZE=10`, `MIN_QUALITY=7` and `MAX_SITE_CHARS=6000`. OA-06 also has `REPORT_EMAIL`.

> Find and replace tip: in each JSON, before import, replace `YOUR_GOOGLE_SHEET_ID`, `you@yourdomain.com`, `approver@yourdomain.com` and `alerts@yourdomain.com`. Then all 7 are filled at once.

## 5. Webhook secret (OA-01 only)

The webhook checks the header `x-webhook-secret` against the env var `OUTREACH_WEBHOOK_SECRET`. It **fails closed**: if the env var is missing or shorter than 16 characters, every call gets a 401.

```bash
# where n8n runs (docker: add to environment:)
export OUTREACH_WEBHOOK_SECRET="$(openssl rand -hex 24)"
export N8N_BLOCK_ENV_ACCESS_IN_NODE=false   # required on n8n 2.x (blocked by default); harmless on 1.x
```

Test it once OA-01 is active (use `/webhook-test/...` while the canvas is listening):

```bash
curl -i -X POST "https://YOUR_N8N/webhook/outreach-intake" \
  -H "Content-Type: application/json" \
  -H "x-webhook-secret: $OUTREACH_WEBHOOK_SECRET" \
  -d '{"prospects":[{"first_name":"Test","email":"you+hook@yourdomain.com","company":"Hook Co","website":"https://www.iana.org","timezone":"Asia/Kolkata"}]}'
# expect 202 {"ok":true,"status":"accepted"}; a wrong or missing header gives 401
```

If you can't set env vars (for example on n8n Cloud), change the Webhook node to **Header Auth**. Create a Header Auth credential named `x-webhook-secret`, then delete the "Secret Valid?" IF and the 401 node.

## 6. Activate

Activate (on n8n 2.x: **Publish**) OA-99 first (error workflows don't need to be active, but this is harmless), then **OA-01 before OA-00**, then OA-02 → OA-06. On n8n 2.x, production form submissions run the **published** version of OA-01, and publishing OA-00 is blocked until OA-01 is published. Test runs from the editor use OA-01's saved draft. Each schedule is independent. Statuses in the sheet are the hand-off between workflows.

```
new_import → new → researching → drafted → pending_approval → approved → sent → followup_1 → followup_2 → no_response
side exits: disqualified · research_failed · rejected · replied · in_conversation · snoozed · unsubscribed · bounced · suppressed · send_failed · followup_failed · reply_failed · needs_review · duplicate_email · duplicate_domain · invalid_email
```

---

## 7. Six test cases (do these before recording)

Set `IGNORE_SEND_WINDOW=true` and `TEST_FOLLOWUP_DELAY_MINUTES=5` in OA-03, OA-04 and OA-05 for testing. Reset them afterwards.

| # | Test | How | Expected |
|---|---|---|---|
| 1 | **Intake and dedupe** | Paste the 8 sample rows, then run OA-01 manually from **Every 15 min: Sheet Imports** (or wait 15 min). Then open **OA-00 Form Intake**, click **Execute workflow** (from *Form: Add Prospect*), and submit the form with a new plus-address; submit it again with the same address. | 6 rows become `new` with a `prospect_id` and `created_at`. The BEN row becomes `duplicate_email` and the Grace row `duplicate_domain`. Events has 8 rows. The first form submit appends a `new` row (source `form`) and the ending page says it was added; the repeat shows *Prospect not added: duplicate_email*. Both log to Events. The webhook curl returns 202, and 401 with a bad header. |
| 2 | **Research and draft** | Run OA-02 manually | Each `new` row goes to `researching`, then `drafted` (real site) or `disqualified` (example.com). Messages gets a `draft` row of 80–120 words in 3 paragraphs, ending with your name. Events shows `drafted` with a score. |
| 3 | **Approve and send** | Run OA-03 Lane A. Open the Gmail approval and choose **Approve with my edits**, changing the subject. Then run Lane B. | The row goes `pending_approval` → `approved` → `sent`, with `thread_id`, `last_message_id` and `next_followup_at` set. Your plus-address receives the edited version. **Reject** on another row gives `rejected`. |
| 4 | **Follow-up** | Wait 5 min, then run OA-04 | A short follow-up arrives **in the same thread**. Status `followup_1`, `followup_count=1`. Run again after 5 min to get `followup_2`; after that you get `no_response`. |
| 5 | **Reply handling** | Reply from the plus-address with "Sounds interesting, what would it cost?" | OA-05 marks it read and classifies it `interested` or `question`. You get an approval email with a suggested reply. On approve, the reply goes out in the thread and the status becomes `in_conversation`. |
| 6 | **Unsubscribe, OOO and bounce** | Reply "please remove me" from another prospect. Reply "I'm out of office until Nov 20" from a third. Add a row with `nobody@invalid-domain-xyz.example` and send. | Unsubscribe: Suppression row, `unsubscribed`, **no reply sent**. OOO: `next_followup_at` = Nov 21. Bounce: mailer-daemon is detected, giving `bounced` and a Suppression row. Bonus: turn off the Sheets credential and run OA-02; the OA-99 alert email and an Errors row appear. |

Stuck rows: if an execution dies mid-way, a prospect can be left in `researching` or `pending_approval`. Set it back to `new` or `drafted` by hand.

---

## 8. Demo video: 8 shots (3–4 min total)

| # | Shot (≈ seconds) | What to show / say |
|---|---|---|
| 1 | **Hook (15s)** | The Prospects sheet with colourful statuses. "This agent researches, writes, sends, follows up and handles replies, and I approve every email from my inbox." |
| 2 | **Architecture (20s)** | The mermaid diagram from ARCHITECTURE.md. Walk the status line from `new` to `in_conversation`. |
| 3 | **Intake (25s)** | Submit the Form (OA-00) and a webhook curl (show the 401 too). Paste the CSV and run OA-01. Duplicates are rejected and appear in Events. |
| 4 | **AI research (35s)** | Open OA-02's execution: the fetched site text, then the agent output JSON (fit, observation, score). Show the regenerate branch on a low score. Show one `disqualified`. |
| 5 | **Human approval (30s)** | The Gmail approval email, then the form (Approve with edits). The sent email arrives in the prospect inbox. The sheet row shows `sent` + `thread_id`. |
| 6 | **Follow-up in thread (25s)** | The same Gmail thread with the 2-line follow-up underneath. Mention the window, the daily cap and the suppression re-check before every send. |
| 7 | **Inbox agent (40s)** | Live reply "how much?", then classification, the approval with the suggested reply, the reply sent, and `in_conversation`. Quick cuts: unsubscribe goes to Suppression; OOO gives the return date. |
| 8 | **Reliability and report (25s)** | The OA-99 alert email and Errors tab, the weekly report email with the Gemini insight. Close: "Idempotent, retry-safe, human-in-the-loop." |
