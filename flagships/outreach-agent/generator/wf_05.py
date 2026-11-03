from common import *
from wf_03 import send_and_wait, DECISION_PARSE

CLASS_SCHEMA = {'type': 'object', 'properties': {
    'category': {'type': 'string', 'enum': ['interested', 'question', 'objection', 'not_now', 'unsubscribe', 'out_of_office', 'bounce', 'other']},
    'summary': {'type': 'string', 'description': 'one sentence summary of the reply'},
    'suggested_reply': {'type': 'string', 'description': 'plain-text reply for interested, question or objection; empty string otherwise'},
    'return_date': {'type': 'string', 'description': 'YYYY-MM-DD the person is back, only for out_of_office, else empty string'}},
    'required': ['category', 'summary', 'suggested_reply', 'return_date']}

MATCH_JS = JS_HELPERS + r'''
const prospects = rowsOf('Load Prospects').filter(r => r.prospect_id);
const byEmail = new Map(prospects.map(p => [lc(p.email), p]));
const byThread = new Map(prospects.filter(p => p.thread_id).map(p => [String(p.thread_id), p]));
const me = lc(CFG.SENDER_EMAIL);
const out = [];
for (const item of $('Gmail Trigger: Unread Inbox').all()) {
  const m = item.json;
  const fromAddr = lc((m.from && m.from.value && m.from.value[0] && m.from.value[0].address) || String(m.From || m.from || '').replace(/.*</, '').replace(/>.*/, ''));
  const subject = String(m.subject || m.Subject || '');
  const text = String(m.text || m.snippet || '').slice(0, 8000);
  if (!fromAddr || fromAddr === me) continue;
  const isBounce = /mailer-daemon|postmaster/.test(fromAddr) || /(delivery status notification|undeliverable|mail delivery failed|returned mail|delivery failure|address not found)/i.test(subject);
  let p = byThread.get(String(m.threadId)) || byEmail.get(fromAddr);
  if (!p && isBounce) p = prospects.find(x => x.email && text.toLowerCase().includes(lc(x.email)));
  if (!p) continue;                       // not a prospect: leave the email alone (stays unread)
  if (['unsubscribed', 'bounced'].includes(p.status)) continue;
  // drop quoted history so the classifier only sees the new reply
  const fresh = text.split(/\n(?:On .{5,200}wrote:|-{2,} ?Original Message|From: .+\nSent: )/i)[0].replace(/^>.*$/gm, '').trim();
  out.push({ json: { prospect_id: p.prospect_id, status_at_match: p.status, email: p.email, domain: p.domain,
    first_name: safe(p.first_name), company: safe(p.company), timezone: p.timezone,
    gmail_id: m.id, thread_id: m.threadId, from: fromAddr, subject: safe(subject).slice(0, 300),
    reply_text: safe(fresh || text).slice(0, 4000), is_bounce: isBounce } });
}
return out;
'''

def build_05(path):
    wf = WF('OA-05 Inbox Agent', '05')
    wf.note('Inbox agent (polls Gmail every minute)', 'Unread INBOX mail → matched to a prospect by **thread_id** or **sender email** (bounces: by the address inside the bounce). Non-prospect mail is ignored and **left unread**.\n\nGemini classifier (structured output) returns category, summary, suggested_reply, return_date, then a Switch routes:\n- **interested / question / objection** → status `replied`, approver gets the suggested reply (send / edit / don\'t send) → reply in thread → `in_conversation`\n- **not_now** → `snoozed`, recontact_at +75 days\n- **unsubscribe** → Suppression + `unsubscribed`, never replies\n- **out_of_office** → next_followup_at = return date + 1 day (status kept)\n- **bounce** (classifier or mailer-daemon) → `bounced` + Suppression\n- **other** → `replied` for you to read\n\nEvery handled email is marked read and logged to Events.', (-100, -720), 800, 520, 4)
    wf.note('Approval pauses the batch', 'Send-and-Wait pauses this execution until you answer, so other replies that arrived in the **same minute** wait too. Answer approvals promptly (or switch the reply step to Gmail **Create Draft** if you prefer to review in Gmail).', (2900, -720), 520, 220, 3)
    t = wf.add('Gmail Trigger: Unread Inbox', 'n8n-nodes-base.gmailTrigger', 'gmailTrigger', {
        'pollTimes': {'item': [{'mode': 'everyMinute'}]}, 'simple': False,
        'filters': {'labelIds': ['INBOX'], 'readStatus': 'unread'}, 'options': {}}, (0, 0))
    wf.ext(t)
    cfg = config(wf, (220, 0))
    lpros = sheet(wf, 'Load Prospects', sheets_read('Prospects'), (440, 0), executeOnce=True, alwaysOutputData=True)
    match = codeN(wf, 'Match to Prospect', MATCH_JS, (660, 0))
    lp = loop(wf, 'Loop Replies', (880, 0))
    wf.chain(t, cfg, lpros, match, lp)
    wf.c(lp, wf.add('Replies Done', 'n8n-nodes-base.noOp', 'noop', {}, (1100, -160)), 0)
    L = "$('Loop Replies').first(1).json"
    rr = reread(wf, 'Re-read Prospect', L + '.prospect_id', (1100, 40))
    wf.c(lp, rr, 1)
    br = switchN(wf, 'Bounce or Reply?', [('mailer_daemon_bounce', L + '.is_bounce'),
                                          ('classify', '!' + L + '.is_bounce && !!$json.prospect_id && !["unsubscribed","bounced"].includes($json.status)'),
                                          ('stop', '!' + L + '.is_bounce && !($json.prospect_id && !["unsubscribed","bounced"].includes($json.status))')], (1320, 40))
    wf.c(rr, br)
    cls = chain_llm(wf, 'AI Classify Reply',
        "=Classify this email reply to a cold outreach message from {{ $('Config').first().json.SENDER_NAME }}, who builds small business automations and offered to send a 2-minute video.\n\n"
        "From: {{ " + L + ".from }}\nSubject: {{ " + L + ".subject }}\nProspect first name: {{ " + L + ".first_name }} | Company: {{ " + L + ".company }}\n\n"
        "Reply text:\n{{ " + L + ".reply_text }}\n\n"
        "Categories: interested (wants the video, a call or more info), question (asks something specific), objection (pushback on price, need, timing with reasons, or trust), "
        "not_now (polite not right now or later this year), unsubscribe (asks to stop, remove, not interested at all), out_of_office (automatic absence reply), "
        "bounce (delivery failure notice), other (anything else).\n"
        "summary: one sentence.\n"
        "suggested_reply: only for interested, question or objection. Plain text, 40 to 90 words, warm and direct, answers what they said, no lists, no links, no buzzwords, "
        "starts with Hi and the first name, ends with Best, and {{ $('Config').first().json.SENDER_NAME }} on separate lines. Never promise prices, dates or results. Otherwise an empty string.\n"
        "return_date: for out_of_office the date they are back as YYYY-MM-DD if stated (today is {{ $now.toISODate() }}), otherwise an empty string.",
        (1580, -60), 'Gemini (Classifier)', 'Parse Classification JSON', CLASS_SCHEMA, 0.2, on_error='continueErrorOutput')
    wf.c(br, cls, 1); wf.c(br, lp, 2)
    norm = codeN(wf, 'Normalise Classification', PARSE_LLM + r'''
const m = $('Loop Replies').first(1).json;
let o = {};
try { o = parseLLM($input.first().json); } catch (e) { o = {}; }
const cats = ['interested','question','objection','not_now','unsubscribe','out_of_office','bounce','other'];
let category = cats.includes(o.category) ? o.category : 'other';
if ($input.first().json.error) category = 'other';
if (/^\s*(unsubscribe|stop|remove me)\b/i.test(m.reply_text)) category = 'unsubscribe';   // hard safety net
return [{ json: { ...m, category, summary: String(o.summary || ($input.first().json.error ? 'classifier failed - please read manually' : '')).slice(0, 400),
  suggested_reply: String(o.suggested_reply || '').trim(), return_date: String(o.return_date || '').trim() } }];
''', (1860, -60))
    wf.c(cls, norm, 0); wf.c(cls, norm, 1)
    bnorm = codeN(wf, 'Bounce Item', r'''
const m = $('Loop Replies').first(1).json;
return [{ json: { ...m, category: 'bounce', summary: 'delivery failure (mailer-daemon)', suggested_reply: '', return_date: '' } }];
''', (1860, 140))
    wf.c(br, bnorm, 0)
    mark = wf.add('Mark Email Read', 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'message', 'operation': 'markAsRead', 'messageId': '={{ $json.gmail_id }}'}, (2080, 0), onError='continueRegularOutput')
    wf.ext(mark)
    wf.c(norm, mark); wf.c(bnorm, mark)
    C = "$('Classified').first().json"
    cl = codeN(wf, 'Classified', r'''
// Gmail markAsRead returns only {id,labelIds}; restore the classified item
const fromNorm = $('Normalise Classification').isExecuted ? $('Normalise Classification').last().json : null;
const fromBounce = $('Bounce Item').isExecuted ? $('Bounce Item').last().json : null;
const pick = [fromNorm, fromBounce].filter(Boolean).find(x => x.prospect_id === $('Loop Replies').first(1).json.prospect_id && x.gmail_id === $('Loop Replies').first(1).json.gmail_id);
return [{ json: pick || fromNorm || fromBounce }];
''', (2300, 0))
    wf.c(mark, cl)
    sw = switchN(wf, 'Route by Category', [
        ('needs_reply', "['interested','question','objection'].includes($json.category)"),
        ('not_now', "$json.category === 'not_now'"),
        ('unsubscribe', "$json.category === 'unsubscribe'"),
        ('out_of_office', "$json.category === 'out_of_office'"),
        ('bounce', "$json.category === 'bounce'"),
        ('other', "$json.category === 'other'")], (2520, 0))
    wf.c(cl, sw)
    # needs reply
    nr = codeN(wf, 'Shape: replied', r'''
const c = $json;
return [{ json: { prospect_id: c.prospect_id, status: 'replied', reply_category: c.category, next_followup_at: '', updated_at: new Date().toISOString() } }];
''', (2780, -360))
    nrw = sheet(wf, 'Set replied (stop follow-ups)', sheets_update('Prospects', 'prospect_id'), (3000, -360))
    lgr = codeN(wf, 'Shape: reply_received Event', r'''
const c = $('Classified').first().json;
return [{ json: { timestamp: new Date().toISOString(), prospect_id: c.prospect_id, workflow: 'OA-05-inbox-agent', event: 'reply_received', detail: `${c.category}: ${c.summary}`.slice(0, 900) } }];
''', (3220, -360))
    lgrw = sheet(wf, 'Log reply_received', sheets_append('Events'), (3440, -360))
    wf.c(sw, nr, 0); wf.chain(nr, nrw, lgr, lgrw)
    esc_html = "String(x ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')"
    ask = send_and_wait(wf, 'Approve Reply (Gmail Send & Wait)',
        "={{ $('Config').first().json.APPROVER_EMAIL }}",
        "=Reply ready for {{ " + C + ".first_name }} ({{ " + C + ".company }}) - {{ " + C + ".category }}",
        "={{ (() => { const c = " + C + "; const e = (x) => " + esc_html + "; return '<p><b>' + e(c.category) + '</b> from ' + e(c.from) + '<br>' + e(c.summary) + '</p><p><b>Their message:</b><br>' + e(c.reply_text).slice(0, 2500).replace(/\\n/g, '<br>') + '</p><hr><p><b>Suggested reply:</b><br>' + e(c.suggested_reply || '(none - write your own in the form)').replace(/\\n/g, '<br>') + '</p>'; })() }}",
        [{'fieldLabel': 'Decision', 'fieldType': 'dropdown', 'requiredField': True,
          'fieldOptions': {'values': [{'option': 'Send suggested reply'}, {'option': 'Send my edited reply below'}, {'option': "Don't send - I'll handle it"}]}},
         {'fieldLabel': 'Edited reply', 'fieldType': 'textarea', 'placeholder': 'Full reply text if you chose to edit'}],
        'Reply approval', 'The reply is sent in the same Gmail thread, only from the sender mailbox.', (3660, -360), hours=24)
    wf.c(lgrw, ask)
    pd = codeN(wf, 'Parse Reply Decision', DECISION_PARSE + r'''
const d = $input.first().json.data;
const c = $('Classified').first().json;
let send = false, body = c.suggested_reply;
if (d) {
  const choice = String(formValue(d, 'Decision')).toLowerCase();
  if (choice.startsWith('send my')) { const eb = String(formValue(d, 'Edited reply') || '').trim(); if (eb) body = eb; send = !!body; }
  else if (choice.startsWith('send')) send = !!body;
}
return [{ json: { send, body, decided: !!d, prospect_id: c.prospect_id } }];
''', (3880, -360))
    rr2 = reread(wf, 'Re-read Before Reply', "$('Parse Reply Decision').first().json.prospect_id", (4100, -360))
    ok = ifN(wf, 'Send Reply?', "$('Parse Reply Decision').first().json.send && ['replied','in_conversation'].includes($json.status)", (4320, -360))
    wf.chain(ask, pd, rr2, ok)
    rep = wf.add('Reply in Thread (Gmail)', 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'message', 'operation': 'reply', 'messageId': '={{ ' + C + '.gmail_id }}',
        'emailType': 'text', 'message': "={{ $('Parse Reply Decision').first().json.body }}",
        'options': {'replyToSenderOnly': True, 'appendAttribution': False, 'senderName': "={{ $('Config').first().json.SENDER_NAME }}"}},
        (4540, -440), onError='continueErrorOutput')
    wf.ext(rep, wait=5000)
    wf.c(ok, rep, 0)
    sm = codeN(wf, 'Shape: Reply Message', r'''
const c = $('Classified').first().json;
const r = $input.first().json;
const now = new Date().toISOString();
return [{ json: { message_key: `${c.prospect_id}-reply-${Date.now()}`, prospect_id: c.prospect_id, email: c.email, domain: c.domain, kind: 'reply',
  subject: 'Re: ' + c.subject, body: $('Parse Reply Decision').first().json.body, quality_score: '', status: 'sent',
  thread_id: r.threadId || c.thread_id, gmail_message_id: r.id || '', created_at: now, sent_at: now } }];
''', (4760, -500))
    smw = sheet(wf, 'Save Reply to Messages', sheets_append('Messages'), (4980, -500))
    sconv = codeN(wf, 'Shape: in_conversation', r'''
const c = $('Classified').first().json;
const r = $('Reply in Thread (Gmail)').first().json;
return [{ json: { prospect_id: c.prospect_id, status: 'in_conversation', last_message_id: r.id || '', updated_at: new Date().toISOString(),
  _event: 'reply_sent', _detail: `answered ${c.category} in thread ${c.thread_id}` } }];
''', (5200, -440))
    wf.c(rep, sm, 0); wf.chain(sm, smw, sconv)
    rfail = codeN(wf, 'Shape: Reply Failed', r'''
const c = $('Classified').first().json; const e = $input.first().json.error;
return [{ json: { prospect_id: c.prospect_id, updated_at: new Date().toISOString(), _event: 'reply_failed', _detail: String((e && (e.message || e)) || '').slice(0, 400) + ' - reply manually from Gmail' } }];
''', (4760, -300))
    wf.c(rep, rfail, 1)
    nosend = codeN(wf, 'Shape: Reply Not Sent', r'''
const d = $('Parse Reply Decision').first().json;
return [{ json: { prospect_id: d.prospect_id, updated_at: new Date().toISOString(), _event: 'reply_not_sent',
  _detail: d.decided ? 'approver chose to handle it manually' : 'no decision within 24h - reply manually' } }];
''', (4540, -220))
    wf.c(ok, nosend, 1)
    # other categories
    snz = codeN(wf, 'Shape: snoozed', JS_HELPERS + r'''
const c = $json;
return [{ json: { prospect_id: c.prospect_id, status: 'snoozed', reply_category: c.category, next_followup_at: '',
  recontact_at: DateTime.utc().plus({ days: 75 }).toISO(), updated_at: nowIso(), _event: 'snoozed', _detail: c.summary } }];
''', (2780, -120))
    uns = codeN(wf, 'Shape: unsubscribe', r'''
const c = $json; const now = new Date().toISOString();
return [{ json: { prospect_id: c.prospect_id, email: c.email, domain: c.domain, reason: 'unsubscribe', added_at: now,
  status: 'unsubscribed', reply_category: c.category, next_followup_at: '', updated_at: now, _event: 'unsubscribed', _detail: c.summary } }];
''', (2780, 20))
    ooo = codeN(wf, 'Shape: out_of_office', JS_HELPERS + r'''
const c = $json;
let back = c.return_date ? DateTime.fromISO(c.return_date, { zone: zoneFor(c.timezone) }) : null;
let next;
if (back && back.isValid && back > DateTime.now().minus({ days: 1 })) next = back.plus({ days: 1 }).set({ hour: 10, minute: 0 }).toUTC().toISO();
else next = addBusinessDays(DateTime.now().setZone(zoneFor(c.timezone)), 5).toUTC().toISO();
return [{ json: { prospect_id: c.prospect_id, reply_category: c.category, next_followup_at: next, updated_at: nowIso(),
  _event: 'out_of_office', _detail: `back ${c.return_date || 'unknown (+5 business days)'}; follow-up moved to ${next}` } }];
''', (2780, 160))
    bnc = codeN(wf, 'Shape: bounce', r'''
const c = $json; const now = new Date().toISOString();
return [{ json: { prospect_id: c.prospect_id, email: c.email, domain: c.domain, reason: 'bounce', added_at: now,
  status: 'bounced', reply_category: 'bounce', next_followup_at: '', updated_at: now, _event: 'bounced', _detail: c.summary } }];
''', (2780, 300))
    oth = codeN(wf, 'Shape: other', r'''
const c = $json;
return [{ json: { prospect_id: c.prospect_id, status: 'replied', reply_category: c.category, next_followup_at: '', updated_at: new Date().toISOString(),
  _event: 'reply_received', _detail: `other: ${c.summary}` } }];
''', (2780, 440))
    wf.c(sw, snz, 1); wf.c(sw, uns, 2); wf.c(sw, ooo, 3); wf.c(sw, bnc, 4); wf.c(sw, oth, 5)
    sup = sheet(wf, 'Add to Suppression', sheets_append('Suppression'), (3020, 160))
    wf.c(uns, sup); wf.c(bnc, sup)
    tail = common_tail(wf, 'OA-05-inbox-agent', 'Loop Replies', (5440, 0))
    for n in (sconv, rfail, nosend, snz, ooo, oth, sup): wf.c(n, tail)
    wf.dump(path)
