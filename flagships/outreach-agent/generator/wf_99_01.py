from lib import *

def write_pair(wf, label, js, tab, op, key, pos, each=False):
    """Code node that shapes rows for a sheet + the Google Sheets write node. returns (first, last)."""
    shape = wf.add(f'Shape: {label}', 'n8n-nodes-base.code', 'code', code(js, each), pos)
    p = sheets_append(tab) if op == 'append' else sheets_update(tab, key)
    verb = 'Append' if op == 'append' else 'Update'
    w = wf.add(f'{verb} {tab}: {label}', 'n8n-nodes-base.googleSheets', 'sheets', p, (pos[0] + 220, pos[1]))
    wf.ext(w)
    wf.c(shape, w)
    return shape, w

# ================= 99 ERROR HANDLER =================
def build_99(path):
    wf = WF('OA-99 Error Handler', '99')
    wf.note('Error handler', 'Every outreach workflow points its **Settings → Error workflow** here.\n\n1. Error Trigger receives the failed execution\n2. Config holds ALERT_EMAIL + SHEET_ID\n3. Format a readable alert\n4. Email the alert **and** append a row to the **Errors** tab (each branch continues even if the other fails).', (-80, -260), 520, 240, 3)
    t = wf.add('Error Trigger', 'n8n-nodes-base.errorTrigger', 'errorTrigger', {}, (0, 100))
    cfg = wf.add('Config', 'n8n-nodes-base.set', 'set', config_params(), (220, 100))
    fmt = wf.add('Format Error Details', 'n8n-nodes-base.code', 'code', code(r'''
const e = $('Error Trigger').first().json;
const ex = e.execution || {};
const trig = e.trigger || {};
const err = ex.error || trig.error || {};
const out = {
  timestamp: new Date().toISOString(),
  workflow: (e.workflow && e.workflow.name) || 'unknown workflow',
  node: ex.lastNodeExecuted || (err.node && err.node.name) || 'n/a (trigger error)',
  error_message: String(err.message || err.description || 'Unknown error').slice(0, 1500),
  execution_id: ex.id || '',
  execution_url: ex.url || '',
  mode: ex.mode || trig.mode || '',
};
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
out.subject = `[Outreach ALERT] ${out.workflow} failed at "${out.node}"`;
out.html = `<h3>Outreach workflow error</h3>
<p><b>Workflow:</b> ${esc(out.workflow)}<br><b>Node:</b> ${esc(out.node)}<br><b>When (UTC):</b> ${out.timestamp}<br><b>Mode:</b> ${esc(out.mode)}</p>
<p><b>Error:</b><br><code>${esc(out.error_message)}</code></p>
${out.execution_url ? `<p><a href="${out.execution_url}">Open the failed execution</a></p>` : '<p>(No execution URL - set N8N_EDITOR_BASE_URL / WEBHOOK_URL on your instance to get links.)</p>'}
<p>Tip: if a prospect is stuck in a transient status (researching / pending_approval), reset its status in the Prospects tab.</p>`;
return [{ json: out }];
'''), (440, 100))
    mail = wf.add('Email Alert', 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'message', 'operation': 'send',
        'sendTo': "={{ $('Config').first().json.ALERT_EMAIL }}", 'subject': '={{ $json.subject }}',
        'emailType': 'html', 'message': '={{ $json.html }}', 'options': {'appendAttribution': False}},
        (680, 0), onError='continueRegularOutput')
    wf.ext(mail)
    s, w = write_pair(wf, 'Error Row', r'''
const e = $('Format Error Details').first().json;
return [{ json: { timestamp: e.timestamp, workflow: e.workflow, node: e.node, error_message: e.error_message,
  execution_id: e.execution_id, execution_url: e.execution_url, mode: e.mode } }];
''', 'Errors', 'append', None, (680, 200))
    for n in wf.nodes:
        if n['name'] == w: n['onError'] = 'continueRegularOutput'
    wf.chain(t, cfg, fmt); wf.c(fmt, mail); wf.c(fmt, s)
    wf.dump(path, error_wf=False)

# ================= 01 INTAKE =================
SUBWF_TRIGGER = 'When Executed by Another Workflow'
FORM_FIELDS = [
    {'fieldLabel': 'First name', 'requiredField': True},
    {'fieldLabel': 'Last name'},
    {'fieldLabel': 'Email', 'fieldType': 'email', 'requiredField': True},
    {'fieldLabel': 'Company'},
    {'fieldLabel': 'Website', 'placeholder': 'https://example.com'},
    {'fieldLabel': 'Timezone', 'placeholder': 'IANA zone, e.g. America/New_York (blank = default)'},
    {'fieldLabel': 'Notes', 'fieldType': 'textarea'}]
NORMALISE_JS = r'''
const CFG = $('Config').first().json;
const FREE = new Set(['gmail.com','googlemail.com','yahoo.com','yahoo.co.in','outlook.com','hotmail.com','live.com','icloud.com','me.com','aol.com','proton.me','protonmail.com','zoho.com','gmx.com','yandex.com','rediffmail.com','msn.com']);
const EMAIL_RE = /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
const clean = (s) => String(s ?? '').replace(/\s+/g, ' ').trim();
// cyrb53: small deterministic 53-bit hash (no crypto module needed). Two seeds -> 28 hex chars.
function cyrb53(str, seed = 0) {
  let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed;
  for (let i = 0; i < str.length; i++) { const ch = str.charCodeAt(i); h1 = Math.imul(h1 ^ ch, 2654435761); h2 = Math.imul(h2 ^ ch, 1597334677); }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507); h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507); h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16).padStart(14, '0');
}
function hostOf(url) {
  let u = clean(url).toLowerCase();
  if (!u) return '';
  if (!/^https?:\/\//.test(u)) u = 'https://' + u;
  try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; }
}
const out = [];
for (const item of $input.all()) {
  const r = item.json;
  const email = clean(r.email).toLowerCase();
  const emailDomain = email.includes('@') ? email.split('@').pop() : '';
  let website = clean(r.website);
  if (website && !/^https?:\/\//i.test(website)) website = 'https://' + website;
  const webHost = hostOf(website);
  // company domain: website host first, else business email domain
  const domain = webHost || (FREE.has(emailDomain) ? '' : emailDomain);
  if (!website && domain) website = 'https://' + domain;
  let tz = clean(r.timezone);
  if (!tz || !DateTime.now().setZone(tz).isValid) tz = CFG.DEFAULT_TIMEZONE;
  const valid = EMAIL_RE.test(email);
  out.push({ json: {
    prospect_id: valid ? 'p_' + cyrb53(email, 1) + cyrb53(email, 7) : '',
    first_name: clean(r.first_name).replace(/^./, c => c.toUpperCase()),
    last_name: clean(r.last_name),
    email, company: clean(r.company), domain, website, timezone: tz,
    source: clean(r.source) || r._source || 'unknown',
    notes: clean(r.notes),
    _source: r._source, _row_number: r._row_number,
    _email_domain: emailDomain, _free_email: FREE.has(emailDomain),
    _valid_email: valid,
  }});
}
return out;
'''

DEDUP_JS = r'''
const lc = (s) => String(s ?? '').trim().toLowerCase();
const candidates = $('Normalise & Validate').all().map(i => i.json);
const existing = $('Load Existing Prospects').all().map(i => i.json)
  .filter(r => r && r.prospect_id && lc(r.status) !== 'new_import');
const supp = $('Load Suppression List').all().map(i => i.json).filter(r => r && (r.email || r.domain));
const emails = new Set(existing.map(r => lc(r.email)).filter(Boolean));
const domains = new Set(existing.map(r => lc(r.domain)).filter(Boolean));
const suppEmails = new Set(supp.map(r => lc(r.email)).filter(Boolean));
const suppDomains = new Set(supp.filter(r => !lc(r.email)).map(r => lc(r.domain)).filter(Boolean));
const seenE = new Set(), seenD = new Set();
const now = new Date().toISOString();
return candidates.map((c) => {
  let decision = 'insert', reason = '';
  if (!c._valid_email) { decision = 'invalid_email'; reason = `invalid email "${c.email}"`; }
  else if (suppEmails.has(c.email) || (c.domain && suppDomains.has(c.domain))) { decision = 'suppressed'; reason = 'on Suppression list'; }
  else if (emails.has(c.email) || seenE.has(c.email)) { decision = 'duplicate_email'; reason = `email already in CRM: ${c.email}`; }
  else if (c.domain && (domains.has(c.domain) || seenD.has(c.domain))) { decision = 'duplicate_domain'; reason = `company domain already in CRM: ${c.domain}`; }
  if (decision === 'insert') { seenE.add(c.email); if (c.domain) seenD.add(c.domain); }
  const fromSheet = c._source === 'sheet_import' && c._row_number;
  const base = decision === 'insert'
    ? { ...c, status: 'new', followup_count: 0, created_at: now, updated_at: now }
    : { status: decision, notes: [c.notes, reason].filter(Boolean).join(' | '), updated_at: now };
  const row = { ...base };
  if (fromSheet) row.row_number = Number(c._row_number);
  return { json: { ...row, _decision: decision, _reason: reason, _from_sheet: !!fromSheet,
                   _event_pid: c.prospect_id, _email: c.email, _source: c._source } };
});
'''

def build_01(path):
    wf = WF('OA-01 Outreach Intake', '01')
    wf.note('1. Three ways in', 'Prospects arrive through:\n- **Form** lives in **OA-00 Form Intake**, which calls this workflow via **When Executed by Another Workflow** (accept all data) -> source `form`. (n8n Form Trigger workflows cannot contain Respond to Webhook nodes, so the form is split out.)\n- **Webhook** `POST /webhook/outreach-intake` with header `x-webhook-secret` (= env `OUTREACH_WEBHOOK_SECRET`). Body: one prospect object, an array, or `{ "prospects": [...] }`\n- **Schedule**: picks up rows pasted into **Prospects** with status `new_import`', (-120, -420), 700, 260, 4)
    wf.note('2. Clean, dedupe, protect', 'Normalise (trim, lowercase email, company domain from website or business email), validate email, then dedupe against the CRM by **email AND company domain** (free-mail domains are never used for domain dedupe) and check the **Suppression** tab. Deterministic `prospect_id` = hash of email.', (980, -420), 640, 260, 5)
    wf.note('3. Write + audit trail', 'New prospects get status `new` (OA-02-research-draft picks them up). Sheet-import rows are updated in place; rejected imports are marked `duplicate_email` / `duplicate_domain` / `suppressed` / `invalid_email`. **Every decision is logged to Events.**', (1900, -420), 640, 260, 6)

    sub = wf.add(SUBWF_TRIGGER, 'n8n-nodes-base.executeWorkflowTrigger', 'execWfTrigger',
                 {'inputSource': 'passthrough'}, (0, -100))
    hook = wf.add('Webhook: Prospect API', 'n8n-nodes-base.webhook', 'webhook', {
        'httpMethod': 'POST', 'path': 'outreach-intake', 'responseMode': 'responseNode', 'options': {}},
        (0, 100), webhookId=uid('01hook'))
    sch = wf.add('Every 15 min: Sheet Imports', 'n8n-nodes-base.scheduleTrigger', 'schedule',
                 {'rule': {'interval': [{'field': 'minutes', 'minutesInterval': 15}]}}, (0, 300))
    cfg = wf.add('Config', 'n8n-nodes-base.set', 'set', config_params(
        [('WEBHOOK_SECRET', "={{ (() => { try { return $env.OUTREACH_WEBHOOK_SECRET || ''; } catch (e) { return ''; } })() }}", 'string')], include_other=True), (220, 100))
    route = wf.add('Route by Source', 'n8n-nodes-base.switch', 'switch', switch_params([
        ('webhook', "$('Webhook: Prospect API').isExecuted"),
        ('form', "$('" + SUBWF_TRIGGER + "').isExecuted"),
        ('sheet_import', "$('Every 15 min: Sheet Imports').isExecuted")], '01route'), (440, 100))
    for t in (sub, hook, sch): wf.c(t, cfg)
    wf.c(cfg, route)
    # webhook branch
    sec = wf.add('Secret Valid?', 'n8n-nodes-base.if', 'if_', if_params(
        "(() => { const s = String($('Config').first().json.WEBHOOK_SECRET || ''); const h = String(($('Webhook: Prospect API').first().json.headers || {})['x-webhook-secret'] || ''); return s.length >= 16 && h === s; })()", '01sec'), (680, -40))
    r401 = wf.add('Respond 401 Unauthorized', 'n8n-nodes-base.respondToWebhook', 'respond', {
        'respondWith': 'json', 'responseBody': '={{ JSON.stringify({ ok: false, error: "unauthorized" }) }}',
        'options': {'responseCode': 401}}, (920, 40))
    r202 = wf.add('Respond 202 Accepted', 'n8n-nodes-base.respondToWebhook', 'respond', {
        'respondWith': 'json', 'responseBody': '={{ JSON.stringify({ ok: true, status: "accepted" }) }}',
        'options': {'responseCode': 202}}, (920, -140))
    mapw = wf.add('Map Webhook Payload', 'n8n-nodes-base.code', 'code', code(r'''
const body = $('Webhook: Prospect API').first().json.body || {};
let list = Array.isArray(body) ? body : (Array.isArray(body.prospects) ? body.prospects : [body]);
list = list.filter(p => p && typeof p === 'object').slice(0, 200);
return list.map(p => ({ json: {
  first_name: p.first_name ?? p.firstName ?? '', last_name: p.last_name ?? p.lastName ?? '',
  email: p.email ?? '', company: p.company ?? '', website: p.website ?? p.url ?? '',
  timezone: p.timezone ?? '', notes: p.notes ?? '', source: p.source || 'webhook', _source: 'webhook' } }));
'''), (1140, -140))
    wf.c(route, sec, 0); wf.c(sec, r202, 0); wf.c(sec, r401, 1); wf.c(r202, mapw)
    # form branch: OA-00 Form Intake calls this workflow via Execute Workflow (the Form Trigger lives in OA-00,
    # because n8n Form Trigger workflows may not contain Respond to Webhook nodes).
    mapf = wf.add('Map Form Payload', 'n8n-nodes-base.code', 'code', code(r'''
// Items come from "OA-00 Form Intake" (Execute Workflow, accept all data).
// Accepts one prospect per item, or { prospects: [...] }. _source is forced to "form" so a caller
// can never target sheet rows (_row_number is not passed through).
const out = [];
for (const item of $('%s').all()) {
  const j = item.json || {};
  const list = Array.isArray(j.prospects) ? j.prospects : [j];
  for (const p of list) {
    if (!p || typeof p !== 'object') continue;
    out.push({ json: {
      first_name: p.first_name ?? p.firstName ?? '', last_name: p.last_name ?? p.lastName ?? '',
      email: p.email ?? '', company: p.company ?? '', website: p.website ?? p.url ?? '',
      timezone: p.timezone ?? '', notes: p.notes ?? '', source: p.source || 'form', _source: 'form' } });
  }
}
return out.slice(0, 200);
''' % SUBWF_TRIGGER), (1140, 100))
    wf.c(route, mapf, 1)
    # schedule branch
    rd = wf.add('Read new_import Rows', 'n8n-nodes-base.googleSheets', 'sheets', sheets_read('Prospects', [('status', 'new_import')]), (680, 300))
    wf.ext(rd)
    maps = wf.add('Map Sheet Rows', 'n8n-nodes-base.code', 'code', code(r'''
return $input.all().filter(i => i.json && i.json.row_number).map(i => ({ json: { ...i.json,
  source: i.json.source || 'sheet_import', _source: 'sheet_import', _row_number: i.json.row_number } }));
'''), (1140, 300))
    wf.c(route, rd, 2); wf.c(rd, maps)
    norm = wf.add('Normalise & Validate', 'n8n-nodes-base.code', 'code', code(NORMALISE_JS), (1380, 100))
    for m in (mapw, mapf, maps): wf.c(m, norm)
    lp = wf.add('Load Existing Prospects', 'n8n-nodes-base.googleSheets', 'sheets', sheets_read('Prospects'), (1600, 100),
                executeOnce=True, alwaysOutputData=True)
    ls = wf.add('Load Suppression List', 'n8n-nodes-base.googleSheets', 'sheets', sheets_read('Suppression'), (1820, 100),
                executeOnce=True, alwaysOutputData=True)
    wf.ext(lp); wf.ext(ls)
    dd = wf.add('Dedupe & Suppression Check', 'n8n-nodes-base.code', 'code', code(DEDUP_JS), (2040, 100))
    wf.chain(norm, lp, ls, dd)
    sw = wf.add('Route by Decision', 'n8n-nodes-base.switch', 'switch', switch_params([
        ('insert_from_sheet', "$json._decision === 'insert' && $json._from_sheet"),
        ('insert_new_row', "$json._decision === 'insert' && !$json._from_sheet"),
        ('reject_sheet_row', "$json._decision !== 'insert' && $json._from_sheet"),
        ('reject_external', "$json._decision !== 'insert' && !$json._from_sheet")], '01dec'), (2260, 100))
    wf.c(dd, sw)
    act = wf.add('Activate Imported Row', 'n8n-nodes-base.googleSheets', 'sheets', sheets_update('Prospects', 'row_number'), (2520, -100))
    app = wf.add('Append New Prospect', 'n8n-nodes-base.googleSheets', 'sheets', sheets_append('Prospects'), (2520, 60))
    rej = wf.add('Mark Import Row Rejected', 'n8n-nodes-base.googleSheets', 'sheets', sheets_update('Prospects', 'row_number'), (2520, 220))
    for n in (act, app, rej): wf.ext(n)
    ev = wf.add('Build Event Rows', 'n8n-nodes-base.code', 'code', code(r'''
const now = new Date().toISOString();
return $input.all().map(i => ({ json: {
  timestamp: now, prospect_id: i.json._event_pid || '', workflow: 'OA-01-intake',
  event: i.json._decision === 'insert' ? 'imported' : 'import_rejected',
  detail: i.json._decision === 'insert' ? `source=${i.json._source}; ${i.json._email}` : `${i.json._decision}: ${i.json._reason}` } }));
'''), (2780, 100))
    log = wf.add('Log to Events', 'n8n-nodes-base.googleSheets', 'sheets', sheets_append('Events'), (3000, 100))
    wf.ext(log)
    wf.c(sw, act, 0); wf.c(sw, app, 1); wf.c(sw, rej, 2); wf.c(sw, ev, 3)
    for n in (act, app, rej): wf.c(n, ev)
    wf.c(ev, log)
    wf.dump(path)


# ================= 00 FORM INTAKE =================
def build_00(path):
    wf = WF('OA-00 Form Intake', '00')
    wf.note('Form intake (calls OA-01)', 'Manual add / demo form. n8n does not allow **Respond to Webhook** nodes in a workflow started by an **n8n Form Trigger**, and OA-01 needs them for its webhook API, so the form lives here.\n\n1. **Form: Add Prospect** collects the fields\n2. **Map Form Fields** shapes them like the webhook payload\n3. **Run OA-01 Intake** (Execute Workflow, by ID, waits) runs OA-01\'s normalise -> dedupe -> append -> Events path with source `form`\n4. **Form Ending** shows whether the prospect was added\n\nSetup: paste OA-01\'s workflow ID into **Run OA-01 Intake** (placeholder `REPLACE_WITH_OA01_INTAKE_WORKFLOW_ID`). Publish OA-01 before publishing this one.', (-80, -380), 760, 300, 4)
    form = wf.add('Form: Add Prospect', 'n8n-nodes-base.formTrigger', 'form', {
        'formTitle': 'Add an outreach prospect',
        'formDescription': 'Adds one prospect to the AI Outreach CRM. The agent researches their site and drafts a note for your approval.',
        'formFields': {'values': FORM_FIELDS},
        'responseMode': 'onReceived',
        'options': {'appendAttribution': False, 'buttonLabel': 'Add prospect'}}, (0, 100), webhookId=uid('00form'))
    mapf = wf.add('Map Form Fields', 'n8n-nodes-base.code', 'code', code(r"""
const f = $('Form: Add Prospect').first().json;
return [{ json: { first_name: f['First name'] || '', last_name: f['Last name'] || '', email: f['Email'] || '',
  company: f['Company'] || '', website: f['Website'] || '', timezone: f['Timezone'] || '', notes: f['Notes'] || '',
  source: 'form', _source: 'form' } }];
"""), (220, 100))
    run = wf.add('Run OA-01 Intake', 'n8n-nodes-base.executeWorkflow', 'execWf', {
        'source': 'database',
        'workflowId': {'__rl': True, 'value': 'REPLACE_WITH_OA01_INTAKE_WORKFLOW_ID', 'mode': 'id'},
        'mode': 'once',
        'options': {'waitForSubWorkflow': True}}, (440, 100), alwaysOutputData=True)
    msg = ("={{ (() => { const p = $('Map Form Fields').first().json; const r = $json || {}; "
           "if (r.event === 'imported') return p.email + ' was added to the CRM with status \"new\". The agent will research the site and draft a note for your approval.'; "
           "if (r.event === 'import_rejected') return p.email + ' was not added: ' + String(r.detail || 'rejected') + '.'; "
           "return p.email + ' was submitted to intake. Check the Events tab in the CRM sheet for the result.'; })() }}")
    end = wf.add('Form Ending', 'n8n-nodes-base.form', 'formPage', {
        'operation': 'completion', 'respondWith': 'text',
        'completionTitle': "={{ $json.event === 'import_rejected' ? 'Prospect not added' : 'Prospect received' }}",
        'completionMessage': msg,
        'options': {}}, (660, 100), webhookId=uid('00end'))
    wf.chain(form, mapf, run, end)
    wf.dump(path, timezone='Asia/Kolkata')
