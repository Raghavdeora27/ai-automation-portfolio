from common import *

def send_and_wait(wf, name, to_expr, subj_expr, msg_expr, fields, title, desc, pos, hours=48):
    n = wf.add(name, 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'message', 'operation': 'sendAndWait',
        'sendTo': to_expr, 'subject': subj_expr, 'message': msg_expr,
        'responseType': 'customForm', 'defineForm': 'fields',
        'formFields': {'values': fields},
        'options': {'limitWaitTime': {'values': {'limitType': 'afterTimeInterval', 'resumeAmount': hours, 'resumeUnit': 'hours'}},
                    'appendAttribution': False, 'messageButtonLabel': 'Review & decide',
                    'responseFormTitle': title, 'responseFormDescription': desc}},
        pos, webhookId=uid(wf.key + name))
    wf.ext(n)
    return n

DECISION_PARSE = r'''
function formValue(data, label) {
  if (!data) return '';
  const want = label.toLowerCase();
  for (const [k, v] of Object.entries(data)) if (k.toLowerCase() === want) return v;
  return '';
}
'''

def build_03(path):
    wf = WF('OA-03 · Approval & Send', '03')
    wf.note('A. Human approval (every 5 min, one draft per run)', 'Gmail **Send and Wait** can only hold one approval per execution, so each run takes **one** `drafted` prospect:\n1. Re-read → still `drafted`? → load its draft from **Messages**\n2. Mark `pending_approval` (so the next run will not pick it again)\n3. Email APPROVER_EMAIL a form: **Approve as written / Approve with my edits / Reject** (+ edited subject/body)\n4. Re-read → still `pending_approval`? → set `approved` / `rejected` / `approval_expired` (no answer in 48 h)\n\nApproving does **not** send - sending happens in lane B, inside the send window.', (-100, -560), 760, 360, 4)
    wf.note('B. Sending (every 15 min)', 'Takes `approved` prospects and sends **only** when:\n- local time in the **prospect\'s timezone** is Mon-Fri 09:00-17:00 (otherwise it stays `approved` and is retried next run)\n- today\'s sends (Events `sent` + `followup_sent` + `reply_sent`) are under **DAILY_CAP**\n- the email/domain is **not** on Suppression (re-checked right before sending)\n\nThen Gmail send → store thread_id + last_message_id → `sent`, next_followup_at = +3 business days.', (-100, 560), 760, 300, 5)
    t1 = wf.add('Every 5 min: Request Approval', 'n8n-nodes-base.scheduleTrigger', 'schedule', {'rule': {'interval': [{'field': 'minutes', 'minutesInterval': 5}]}}, (0, -40))
    t2 = wf.add('Every 15 min: Send Approved', 'n8n-nodes-base.scheduleTrigger', 'schedule', {'rule': {'interval': [{'field': 'minutes', 'minutesInterval': 15}]}}, (0, 300))
    cfg = config(wf, (220, 120))
    lane = ifN(wf, 'Approval Lane?', "$('Every 5 min: Request Approval').isExecuted", (440, 120))
    wf.c(t1, cfg); wf.c(t2, cfg); wf.c(cfg, lane)

    # ---------------- Lane A: approval ----------------
    rd = sheet(wf, 'Read Drafted Prospects', sheets_read('Prospects', [('status', 'drafted')]), (680, -40))
    one = wf.add('Take One', 'n8n-nodes-base.limit', 'limit', {'maxItems': 1}, (900, -40))
    rr = reread(wf, 'Re-read Drafted Row', '$json.prospect_id', (1120, -40))
    still = ifN(wf, 'Still drafted?', "$json.status === 'drafted'", (1340, -40))
    ld = sheet(wf, 'Load Draft Message', sheets_read('Messages', [('prospect_id', "={{ $('Re-read Drafted Row').first().json.prospect_id }}"), ('status', 'draft')]), (1560, -100), alwaysOutputData=True)
    pick = codeN(wf, 'Pick Latest Draft', r'''
const rows = $input.all().map(i => i.json).filter(r => r && r.message_key && r.kind === 'initial');
const p = $('Re-read Drafted Row').first().json;
const msg = rows.length ? rows[rows.length - 1] : null;
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const html = msg ? `<p><b>To:</b> ${esc(p.first_name)} ${esc(p.last_name)} &lt;${esc(p.email)}&gt; - ${esc(p.company)} (${esc(p.website)})<br>
<b>Prospect timezone:</b> ${esc(p.timezone)}<br><b>Why it fits:</b> ${esc(p.fit_reason)}<br><b>Observation used:</b> ${esc(p.observation)}<br>
<b>Quality score:</b> ${esc(msg.quality_score)}/10</p><hr><p><b>Subject:</b> ${esc(msg.subject)}</p><p>${esc(msg.body).replace(/\n/g, '<br>')}</p><hr>
<p>To edit: choose "Approve with my edits below" and paste the corrected subject and/or body. Blank edit fields keep the original.</p>` : '';
return [{ json: { found: !!msg, prospect_id: p.prospect_id, message_key: msg ? msg.message_key : '', approval_html: html,
  subject: msg ? msg.subject : '', body: msg ? msg.body : '' } }];
''', (1780, -100))
    found = ifN(wf, 'Draft Found?', '$json.found', (2000, -100))
    wf.c(lane, rd, 0); wf.chain(rd, one, rr, still); wf.c(still, ld, 0); wf.chain(ld, pick, found)
    lost = codeN(wf, 'Shape: Draft Missing', r'''
const p = $('Pick Latest Draft').first().json;
return [{ json: { prospect_id: p.prospect_id, status: 'new', updated_at: new Date().toISOString(),
  _event: 'draft_missing', _detail: 'no draft row in Messages - sent back to research (status new)' } }];
''', (2240, 80))
    wf.c(found, lost, 1)
    pend = codeN(wf, 'Shape: pending_approval', r'''
const p = $('Pick Latest Draft').first().json;
return [{ json: { prospect_id: p.prospect_id, status: 'pending_approval', updated_at: new Date().toISOString() } }];
''', (2240, -160))
    pendw = sheet(wf, 'Mark pending_approval', sheets_update('Prospects', 'prospect_id'), (2460, -160))
    wf.c(found, pend, 0); wf.c(pend, pendw)
    ask = send_and_wait(wf, 'Ask Approver (Gmail Send & Wait)',
        "={{ $('Config').first().json.APPROVER_EMAIL }}",
        "=Approve outreach to {{ $('Re-read Drafted Row').first().json.company || $('Re-read Drafted Row').first().json.email }}?",
        "={{ $('Pick Latest Draft').first().json.approval_html }}",
        [{'fieldLabel': 'Decision', 'fieldType': 'dropdown', 'requiredField': True,
          'fieldOptions': {'values': [{'option': 'Approve as written'}, {'option': 'Approve with my edits below'}, {'option': 'Reject'}]}},
         {'fieldLabel': 'Edited subject', 'placeholder': 'Only if you chose edits - leave blank to keep the original'},
         {'fieldLabel': 'Edited body', 'fieldType': 'textarea', 'placeholder': 'Only if you chose edits - paste the full corrected email'},
         {'fieldLabel': 'Note', 'placeholder': 'Optional reason (saved to Events)'}],
        'Outreach approval', 'Approve, edit or reject this AI-drafted email. Nothing is sent until it is inside the send window.',
        (2680, -160))
    wf.c(pendw, ask)
    parse = codeN(wf, 'Parse Decision', DECISION_PARSE + r'''
const d = $input.first().json.data;
const draft = $('Pick Latest Draft').first().json;
let decision = 'expired', subject = draft.subject, body = draft.body;
if (d) {
  const choice = String(formValue(d, 'Decision')).toLowerCase();
  if (choice.startsWith('reject')) decision = 'rejected';
  else if (choice.includes('edit')) {
    decision = 'approved_edited';
    const es = String(formValue(d, 'Edited subject') || '').trim();
    const eb = String(formValue(d, 'Edited body') || '').trim();
    if (es) subject = es;
    if (eb) body = eb;
  } else if (choice) decision = 'approved';
}
return [{ json: { decision, subject, body, note: String(d ? formValue(d, 'Note') : '').slice(0, 300),
  prospect_id: draft.prospect_id, message_key: draft.message_key } }];
''', (2900, -160))
    rr2 = reread(wf, 'Re-read After Decision', "$('Parse Decision').first().json.prospect_id", (3120, -160))
    held = ifN(wf, 'Still pending_approval?', "$json.status === 'pending_approval'", (3340, -160))
    wf.chain(ask, parse, rr2, held)
    sm = codeN(wf, 'Shape: Message Decision', r'''
const d = $('Parse Decision').first().json;
const map = { approved: 'approved', approved_edited: 'approved', rejected: 'rejected', expired: 'approval_expired' };
const out = { message_key: d.message_key, status: map[d.decision] };
if (d.decision === 'approved_edited') { out.subject = d.subject; out.body = d.body; }
return [{ json: out }];
''', (3560, -240))
    smw = sheet(wf, 'Update Message Status', sheets_update('Messages', 'message_key'), (3780, -240))
    sp = codeN(wf, 'Shape: Prospect Decision', r'''
const d = $('Parse Decision').first().json;
const status = { approved: 'approved', approved_edited: 'approved', rejected: 'rejected', expired: 'approval_expired' }[d.decision];
return [{ json: { prospect_id: d.prospect_id, status, updated_at: new Date().toISOString(),
  _event: d.decision === 'expired' ? 'approval_expired' : (status === 'approved' ? (d.decision === 'approved_edited' ? 'approved_with_edits' : 'approved') : 'rejected'),
  _detail: d.note || (d.decision === 'expired' ? 'no answer within 48h - set status back to drafted to ask again' : '') } }];
''', (4000, -160))
    wf.c(held, sm, 0); wf.c(sm, smw); wf.c(smw, sp)
    endA = wf.add('Changed Elsewhere - Stop', 'n8n-nodes-base.noOp', 'noop', {}, (3560, 0))
    wf.c(held, endA, 1)
    upA = sheet(wf, 'Update Prospect (Approval)', sheets_update('Prospects', 'prospect_id'), (4220, -160))
    evA = codeN(wf, 'Build Event Row (Approval)', r'''
return $input.all().map(i => ({ json: { timestamp: new Date().toISOString(), prospect_id: i.json.prospect_id, workflow: 'OA-03-approval-send',
  event: i.json._event, detail: String(i.json._detail || '').slice(0, 900) } }));
''', (4440, -160))
    lgA = sheet(wf, 'Log Event (Approval)', sheets_append('Events'), (4660, -160))
    wf.c(sp, upA); wf.c(lost, upA); wf.chain(upA, evA, lgA)

    # ---------------- Lane B: send ----------------
    ra = sheet(wf, 'Read Approved Prospects', sheets_read('Prospects', [('status', 'approved')]), (680, 300))
    le = sheet(wf, 'Load Events (cap)', sheets_read('Events'), (900, 300), executeOnce=True, alwaysOutputData=True)
    ls = sheet(wf, 'Load Suppression', sheets_read('Suppression'), (1120, 300), executeOnce=True, alwaysOutputData=True)
    plan = codeN(wf, 'Plan Sends (window, cap, suppression)', JS_HELPERS + r'''
const approved = rowsOf('Read Approved Prospects').filter(r => r.prospect_id && r.status === 'approved');
const sentToday = sentTodayCount(rowsOf('Load Events (cap)'));
const supp = rowsOf('Load Suppression');
let budget = Math.max(0, Number(CFG.DAILY_CAP || 30) - sentToday);
const out = [];
for (const p of approved) {
  if (isSuppressed(p.email, p.domain, supp)) { out.push({ json: { ...p, _plan: 'suppress' } }); continue; }
  const w = sendWindow(p.timezone);
  if (!w.ok) continue;            // stays approved; retried next run
  if (budget <= 0) continue;      // cap reached; stays approved
  budget--;
  out.push({ json: { ...p, _plan: 'send', _local: `${w.zone} ${w.local}` } });
}
return out;
''', (1340, 300))
    wf.c(lane, ra, 1); wf.chain(ra, le, ls, plan)
    lp = loop(wf, 'Loop Sends', (1560, 300))
    wf.c(plan, lp)
    wf.c(lp, wf.add('Sends Done', 'n8n-nodes-base.noOp', 'noop', {}, (1780, 160)), 0)
    L = "$('Loop Sends').first(1).json"
    rr3 = reread(wf, 'Re-read Before Send', L + '.prospect_id', (1780, 340))
    lm = sheet(wf, 'Load Approved Message', sheets_read('Messages', [('prospect_id', '={{ ' + L + '.prospect_id }}'), ('status', 'approved')]), (2000, 340), alwaysOutputData=True)
    lss = sheet(wf, 'Re-check Suppression', sheets_read('Suppression', [('email', '={{ ' + L + '.email }}')]), (2220, 340), alwaysOutputData=True)
    prep = codeN(wf, 'Prepare Send', r'''
const plan = $('Loop Sends').first(1).json;
const p = $('Re-read Before Send').first().json;
const msgs = $('Load Approved Message').all().map(i => i.json).filter(r => r && r.message_key && r.kind === 'initial');
const msg = msgs.length ? msgs[msgs.length - 1] : null;
const supp = $input.all().some(i => i.json && i.json.email);
let action = 'send';
if (p.status !== 'approved') action = 'skip';
else if (plan._plan === 'suppress' || supp) action = 'suppress';
else if (!msg) action = 'no_message';
return [{ json: { action, prospect_id: plan.prospect_id, email: p.email, timezone: p.timezone,
  message_key: msg ? msg.message_key : '', subject: msg ? msg.subject : '', body: msg ? msg.body : '' } }];
''', (2440, 340))
    wf.chain(lp, rr3)  # placeholder removed below
    wf.conns['Loop Sends']['main'][0] = [{'node': 'Sends Done', 'type': 'main', 'index': 0}]
    wf.conns['Loop Sends']['main'] = [[{'node': 'Sends Done', 'type': 'main', 'index': 0}], [{'node': rr3, 'type': 'main', 'index': 0}]]
    wf.chain(rr3, lm, lss, prep)
    route = switchN(wf, 'Route Send Action', [('send', "$json.action === 'send'"), ('suppress', "$json.action === 'suppress'"),
                                               ('no_message', "$json.action === 'no_message'"), ('skip', "$json.action === 'skip'")], (2660, 340))
    wf.c(prep, route)
    send = wf.add('Send Email (Gmail)', 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'message', 'operation': 'send', 'sendTo': '={{ $json.email }}', 'subject': '={{ $json.subject }}',
        'emailType': 'text', 'message': '={{ $json.body }}',
        'options': {'appendAttribution': False, 'senderName': "={{ $('Config').first().json.SENDER_NAME }}"}},
        (2900, 200), onError='continueErrorOutput')
    wf.ext(send, wait=5000)
    wf.c(route, send, 0)
    sentm = codeN(wf, 'Shape: Message Sent', r'''
const s = $('Prepare Send').first().json;
const r = $input.first().json;
return [{ json: { message_key: s.message_key, status: 'sent', thread_id: r.threadId, gmail_message_id: r.id, sent_at: new Date().toISOString() } }];
''', (3120, 140))
    sentmw = sheet(wf, 'Update Message: sent', sheets_update('Messages', 'message_key'), (3340, 140))
    sentp = codeN(wf, 'Shape: Prospect Sent', JS_HELPERS + r'''
const s = $('Prepare Send').first().json;
const r = $('Send Email (Gmail)').first().json;
return [{ json: { prospect_id: s.prospect_id, status: 'sent', thread_id: r.threadId, last_message_id: r.id, followup_count: 0,
  next_followup_at: nextFollowupIso(CFG.FOLLOWUP_1_DELAY_BUSINESS_DAYS || 3, s.timezone), updated_at: nowIso(),
  _event: 'sent', _detail: `thread ${r.threadId}; subject "${s.subject}"` } }];
''', (3560, 140))
    wf.c(send, sentm, 0); wf.chain(sentm, sentmw, sentp)
    failp = codeN(wf, 'Shape: Send Failed', r'''
const s = $('Prepare Send').first().json;
const e = $input.first().json.error;
return [{ json: { prospect_id: s.prospect_id, status: 'send_failed', updated_at: new Date().toISOString(),
  _event: 'send_failed', _detail: String((e && (e.message || e)) || 'unknown Gmail error').slice(0, 500) } }];
''', (3120, 300))
    wf.c(send, failp, 1)
    supp = codeN(wf, 'Shape: Suppressed', r'''
return [{ json: { prospect_id: $json.prospect_id, status: 'suppressed', updated_at: new Date().toISOString(),
  _event: 'send_blocked_suppressed', _detail: 'email/domain found on Suppression right before sending' } }];
''', (2900, 420))
    nom = codeN(wf, 'Shape: No Approved Message', r'''
return [{ json: { prospect_id: $json.prospect_id, status: 'new', updated_at: new Date().toISOString(),
  _event: 'draft_missing', _detail: 'approved but no approved row in Messages - sent back to research' } }];
''', (2900, 560))
    wf.c(route, supp, 1); wf.c(route, nom, 2); wf.c(route, lp, 3)
    tail = common_tail(wf, 'OA-03-approval-send', 'Loop Sends', (3800, 340))
    for n in (sentp, failp, supp, nom): wf.c(n, tail)
    wf.dump(path)
