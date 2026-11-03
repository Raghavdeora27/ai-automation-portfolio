# How to import a workflow

These are the steps I follow, and that a client's team can follow, to bring a workflow from this repo into their own account. Not every folder has an export yet. Each workflow README says what's in its folder.

For the **OA (Outreach Agent)** flagship, follow [flagships/outreach-agent/SETUP.md](../flagships/outreach-agent/SETUP.md) instead. It has a strict import order and two workflow-ID placeholders to fill.

## n8n

1. Open the n8n instance.
2. Go to **Workflows**.
3. Choose **Import from File**.
4. Select the workflow JSON in that folder.
5. Reconnect each credential in the n8n credential store. Use the credential names in the workflow README.
6. Fill the config variables in that README, and leave `dry_run` on for the first test.
7. Run the folder's test checklist against `sample-data/` before activating the workflow.

## Make

1. Create a scenario, or open an empty one.
2. Open the scenario menu.
3. Choose **Import Blueprint**.
4. Select the blueprint JSON in that folder.
5. Map every module to a connection in the client's Make account.
6. Fill the scenario variables listed in the workflow README.
7. Run once with the sample payload before turning the scenario on.

## Zapier

Zapier does not import a JSON file the way n8n and Make do. Workflows 13 and 14 ship as a shared Zap link or a Zap template, or they are rebuilt from the folder README.

When a folder contains a shared link or a template URL:

1. Open the shared Zap link or the template URL named in that workflow's README.
2. Choose **Try this Zap** and select the client's Zapier account.
3. Reconnect each app. Use the credential names in the workflow README. Zapier stores the secrets in the client's connections.
4. Fill the input fields listed in that README, including the Storage by Zapier key prefix, and leave `dry_run` on for the first test.
5. Leave the Zap off until the folder's test checklist has been run against `sample-data/`.

When the folder has no shared link yet, rebuild the Zap from the README:

1. Create a Zap in the client's account and leave it off.
2. Set the trigger named in that workflow's README. Workflow 13 uses Webhooks by Zapier Catch Hook and receives Stripe-format payloads there. A Catch Hook that stands in for a signed app still verifies the signature before any write, which is how workflows 04 and 05 are designed. Slack's own connection holds the Slack signing secret.
3. Add each action in the flow order: the allowlist filter, the Storage by Zapier idempotency key, the app actions, and the ops webhook step on the error path.
4. Map fields from the sample payload in `sample-data/`.
5. Run a test with that sample and `dry_run` on. Turn the Zap on only after the checklist passes.
