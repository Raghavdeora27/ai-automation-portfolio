from common import *

FOLLOW_SCHEMA = {'type': 'object', 'properties': {
    'body': {'type': 'string', 'description': '2-3 short lines of plain text plus sign-off'}}, 'required': ['body']}

def build_04(path):
    wf = WF('OA-04 Follow-ups', '04')
    wf.note('Follow-ups (hourly)', 'Finds prospects in `sent` / `followup_1` / `followup_2` whose **next_followup_at** is due, then per prospect:\n1. Re-read status (skip if it changed)\n2. Get the **Gmail thread** - any message not from SENDER_EMAIL → `replied` (OA-05-inbox-agent handles the reply); a mailer-daemon message → `bounced` + Suppression\n3. Already sent 2 follow-ups → `no_response`\n4. Otherwise Gemini writes a 2-3 line nudge, replied **in the same thread**:\n   sent → `followup_1` (+4 business days) → `followup_2` → `no_response`\n\nSending respects the send window, DAILY_CAP and Suppression exactly like 03. Reply/bounce detection runs any time.', (-100, -560), 780, 380, 4)
    t = wf.add('Every Hour', 'n8n-nodes-base.scheduleTrigger', 'schedule', {'rule': {'interval': [{'field': 'hours', 'hoursInterval': 1}]}}, (0, 0))
    cfg = config(wf, (220, 0))
    rd = sheet(wf, 'Read All Prospects', sheets_read('Prospects'), (440, 0))
    le = sheet(wf, 'Load Events (cap)', sheets_read('Events'), (660, 0), executeOnce=True, alwaysOutputData=True)
    ls = sheet(wf, 'Load Suppression', sheets_read('Suppression'), (880, 0), executeOnce=True, alwaysOutputData=True)
    plan = codeN(wf, 'Select Due Follow-ups', JS_HELPERS + r'''
const now = Date.now();
const due = rowsOf('Read All Prospects').filter(r => ['sent', 'followup_1', 'followup_2'].includes(r.status) && r.prospect_id &&
  r.thread_id && r.next_followup_at && Date.parse(r.next_followup_at) <= now);
const supp = rowsOf('Load Suppression');
let budget = Math.max(0, Number(CFG.DAILY_CAP || 30) - sentTodayCount(rowsOf('Load Events (cap)')));
return due.slice(0, 25).map(p => {
  const suppressed = isSuppressed(p.email, p.domain, supp);
  const w = sendWindow(p.timezone);
  let can_send = !suppressed && w.ok && budget > 0 && p.status !== 'followup_2';
  if (can_send) budget--;
  return { json: { ...p, _planned_status: p.status, _suppressed: suppressed, _can_send: can_send,
    _why_not: suppressed ? 'suppressed' : (!w.ok ? `outside send window (${w.zone} ${w.local})` : (budget <= 0 && !can_send ? 'daily cap reached' : '')) } };
});
''', (1100, 0))
    lp = loop(wf, 'Loop Follow-ups', (1320, 0))
    wf.chain(t, cfg, rd, le, ls, plan, lp)
    wf.c(lp, wf.add('Follow-ups Done', 'n8n-nodes-base.noOp', 'noop', {}, (1540, -160)), 0)
    L = "$('Loop Follow-ups').first(1).json"
    rr = reread(wf, 'Re-read Prospect', L + '.prospect_id', (1540, 40))
    wf.c(lp, rr, 1)
    same = ifN(wf, 'Status Unchanged?', "$json.status === " + L + "._planned_status", (1760, 40))
    wf.c(rr, same); wf.c(same, lp, 1)
    th = wf.add('Get Gmail Thread', 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'thread', 'operation': 'get', 'threadId': '={{ ' + L + '.thread_id }}', 'simple': True, 'options': {}},
        (1980, 0), onError='continueErrorOutput')
    wf.ext(th)
    wf.c(same, th, 0)
    dec = codeN(wf, 'Decide Next Step', JS_HELPERS + r'''
const p = $('Loop Follow-ups').first(1).json;
const t = $input.first().json;
const me = lc(CFG.SENDER_EMAIL);
const msgs = Array.isArray(t.messages) ? t.messages : [];
const isSent = (m) => (m.labels || []).some(l => l.id === 'SENT') || (m.labelIds || []).includes('SENT');
const fromOf = (m) => lc(m.From || m.from || '');
const bounce = msgs.find(m => /mailer-daemon|postmaster/.test(fromOf(m)));
const isAuto = (m) => /(out of (the )?office|automatic reply|auto[- ]?reply|autoreply|on (annual )?leave|away from (my|the) (desk|office)|currently away|vacation)/i.test(String(m.Subject || '') + ' ' + String(m.snippet || ''));
const reply = msgs.find(m => !isSent(m) && !fromOf(m).includes(me) && !/mailer-daemon|postmaster/.test(fromOf(m)) && !isAuto(m));
const lastOurs = [...msgs].reverse().find(m => isSent(m) || fromOf(m).includes(me));
const base = { prospect_id: p.prospect_id, updated_at: nowIso() };
let action, out;
if (bounce) { action = 'bounce'; out = { ...base, status: 'bounced', next_followup_at: '', email: p.email, domain: p.domain, reason: 'bounce', added_at: nowIso(), _event: 'bounced', _detail: String(bounce.snippet || '').slice(0, 300) }; }
else if (reply) { action = 'update'; out = { ...base, status: 'replied', next_followup_at: '', _event: 'reply_detected', _detail: `reply in thread from ${reply.From || 'prospect'} - handled by OA-05-inbox-agent` }; }
else if (p._suppressed) { action = 'update'; out = { ...base, status: 'suppressed', next_followup_at: '', _event: 'followup_blocked_suppressed', _detail: 'on Suppression list' }; }
else if (p.status === 'followup_2') { action = 'update'; out = { ...base, status: 'no_response', next_followup_at: '', _event: 'no_response', _detail: 'no reply after 2 follow-ups' }; }
else if (!p._can_send) { action = 'skip'; out = { ...base, _detail: p._why_not }; }
else {
  action = 'write';
  const n = Number(p.followup_count || 0) + 1;
  out = { ...base, n, reply_to_id: (lastOurs && lastOurs.id) || p.last_message_id, thread_id: p.thread_id, email: p.email, domain: p.domain,
    first_name: safe(p.first_name), company: safe(p.company), observation: safe(p.observation), timezone: p.timezone,
    first_subject: safe((msgs[0] && msgs[0].Subject) || ''), first_snippet: safe((msgs[0] && msgs[0].snippet) || '') };
}
return [{ json: { action, ...out } }];
''', (2200, 0))
    tfail = codeN(wf, 'Shape: Thread Missing', r'''
const p = $('Loop Follow-ups').first(1).json;
const e = $input.first().json.error;
return [{ json: { prospect_id: p.prospect_id, status: 'needs_review', updated_at: new Date().toISOString(),
  _event: 'thread_missing', _detail: 'could not load Gmail thread: ' + String((e && (e.message || e)) || '').slice(0, 300) } }];
''', (2200, 260))
    wf.c(th, dec, 0); wf.c(th, tfail, 1)
    sw = switchN(wf, 'Route Next Step', [('write_followup', "$json.action === 'write'"), ('bounce', "$json.action === 'bounce'"),
                                         ('update_status', "$json.action === 'update'"), ('skip', "$json.action === 'skip'")], (2420, 0))
    wf.c(dec, sw)
    llm = chain_llm(wf, 'AI Write Follow-up',
        "=Write follow-up number {{ $json.n }} to a cold email that got no reply.\n\n"
        "Prospect first name: {{ $json.first_name }}\nCompany: {{ $json.company }}\nWhat we noticed on their site: {{ $json.observation }}\n"
        "Original subject: {{ $json.first_subject }}\nStart of the original email: {{ $json.first_snippet }}\n\n"
        "Rules: 2 to 3 short lines of plain text, then a blank line, then Best, and {{ $('Config').first().json.SENDER_NAME }} on separate lines. "
        "Start with Hi and the first name. Do not repeat the first email. Follow-up 1 adds one small new angle and repeats the offer of a 2-minute video. "
        "Follow-up 2 is a polite last note saying you will not keep emailing, and leaves the door open. "
        "No guilt-tripping phrases like just bumping this or circling back, no lists, no links, no buzzwords, no exclamation marks.",
        (2680, -200), 'Gemini (Follow-up)', 'Parse Follow-up JSON', FOLLOW_SCHEMA, 0.6)
    wf.c(sw, llm, 0)
    prep = codeN(wf, 'Prepare Follow-up', PARSE_LLM + r'''
const d = $('Decide Next Step').first().json;
const o = parseLLM($input.first().json);
const body = String(o.body || o._raw || '').trim();
return [{ json: { ...d, body, ok: body.length > 20 } }];
''', (2960, -200))
    rr2 = reread(wf, 'Re-read Before Follow-up', "$('Decide Next Step').first().json.prospect_id", (3180, -200))
    ok = ifN(wf, 'Still Due & Body OK?', "$json.status === " + L + "._planned_status && $('Prepare Follow-up').first().json.ok", (3400, -200))
    wf.chain(llm, prep, rr2, ok)
    wf.c(ok, lp, 1)
    rep = wf.add('Reply in Thread (Gmail)', 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'thread', 'operation': 'reply',
        'threadId': "={{ $('Prepare Follow-up').first().json.thread_id }}",
        'messageId': "={{ $('Prepare Follow-up').first().json.reply_to_id }}",
        'emailType': 'text', 'message': "={{ $('Prepare Follow-up').first().json.body }}",
        'options': {'replyToRecipientsOnly': True, 'senderName': "={{ $('Config').first().json.SENDER_NAME }}"}},
        (3620, -260), onError='continueErrorOutput')
    wf.ext(rep, wait=5000)
    wf.c(ok, rep, 0)
    sm = codeN(wf, 'Shape: Follow-up Message', r'''
const f = $('Prepare Follow-up').first().json;
const r = $input.first().json;
const now = new Date().toISOString();
return [{ json: { message_key: `${f.prospect_id}-followup${f.n}-${Date.now()}`, prospect_id: f.prospect_id, email: f.email, domain: f.domain,
  kind: `followup_${f.n}`, subject: 'Re: ' + f.first_subject, body: f.body, quality_score: '', status: 'sent',
  thread_id: r.threadId || f.thread_id, gmail_message_id: r.id || '', created_at: now, sent_at: now } }];
''', (3840, -320))
    smw = sheet(wf, 'Save Follow-up to Messages', sheets_append('Messages'), (4060, -320))
    sp = codeN(wf, 'Shape: Prospect Followed-up', JS_HELPERS + r'''
const f = $('Prepare Follow-up').first().json;
const r = $('Reply in Thread (Gmail)').first().json;
const status = f.n >= 2 ? 'followup_2' : 'followup_1';
// after follow-up 1 wait FOLLOWUP_2_DELAY; after follow-up 2 wait the same again before closing as no_response
const next = nextFollowupIso(CFG.FOLLOWUP_2_DELAY_BUSINESS_DAYS || 4, f.timezone);
return [{ json: { prospect_id: f.prospect_id, status, followup_count: f.n, last_message_id: r.id || f.reply_to_id, next_followup_at: next,
  updated_at: nowIso(), _event: 'followup_sent', _detail: `follow-up ${f.n} in thread ${f.thread_id}` } }];
''', (4280, -260))
    wf.c(rep, sm, 0); wf.chain(sm, smw, sp)
    rfail = codeN(wf, 'Shape: Follow-up Failed', r'''
const f = $('Prepare Follow-up').first().json;
const e = $input.first().json.error;
return [{ json: { prospect_id: f.prospect_id, updated_at: new Date().toISOString(), _event: 'followup_failed',
  _detail: String((e && (e.message || e)) || 'Gmail error').slice(0, 400) + ' (will retry next hour)' } }];
''', (3840, -120))
    wf.c(rep, rfail, 1)
    sup = sheet(wf, 'Add Bounce to Suppression', sheets_append('Suppression'), (2680, 120))
    wf.c(sw, sup, 1)
    wf.c(sw, lp, 3)
    tail = common_tail(wf, 'OA-04-followups', 'Loop Follow-ups', (4500, 0))
    for n in (sp, rfail, sup, tfail): wf.c(n, tail)
    wf.c(sw, tail, 2)
    wf.dump(path)
