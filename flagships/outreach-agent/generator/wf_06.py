from common import *

def build_06(path):
    wf = WF('OA-06 Weekly Report', '06')
    wf.note('Weekly report (Mondays 09:00)', 'Counts the last 7 days from **Events** (imported, drafted, approved, sent, follow-ups, replies by category, bounces, unsubscribes) plus the current pipeline from **Prospects**, asks Gemini for a 3-line insight, and emails an HTML report to REPORT_EMAIL.\n\nThe 09:00 uses the workflow timezone (**Settings → Timezone**, set to Asia/Kolkata in this file).', (-100, -380), 640, 260, 4)
    t = wf.add('Every Monday 09:00', 'n8n-nodes-base.scheduleTrigger', 'schedule', {'rule': {'interval': [
        {'field': 'weeks', 'weeksInterval': 1, 'triggerAtDay': [1], 'triggerAtHour': 9, 'triggerAtMinute': 0}]}}, (0, 0))
    cfg = config(wf, (220, 0), [('REPORT_EMAIL', 'you@yourdomain.com', 'string')])
    ev = sheet(wf, 'Read Events', sheets_read('Events'), (440, 0), executeOnce=True, alwaysOutputData=True)
    pr = sheet(wf, 'Read Prospects', sheets_read('Prospects'), (660, 0), executeOnce=True, alwaysOutputData=True)
    m = codeN(wf, 'Compute Metrics', r'''
const lc = (s) => String(s ?? '').trim().toLowerCase();
const since = Date.now() - 7 * 864e5;
const events = $('Read Events').all().map(i => i.json).filter(r => r && r.timestamp && Date.parse(r.timestamp) >= since);
const prospects = $('Read Prospects').all().map(i => i.json).filter(r => r && r.prospect_id);
const count = (name) => events.filter(e => lc(e.event) === name).length;
const replyCats = {};
for (const e of events.filter(e => lc(e.event) === 'reply_received')) {
  const cat = String(e.detail || '').split(':')[0].trim() || 'other'; replyCats[cat] = (replyCats[cat] || 0) + 1;
}
const pipeline = {};
for (const p of prospects) pipeline[p.status || 'blank'] = (pipeline[p.status || 'blank'] || 0) + 1;
const sent = count('sent'), fu = count('followup_sent'), replies = count('reply_received');
const metrics = {
  period: `${new Date(since).toISOString().slice(0, 10)} to ${new Date().toISOString().slice(0, 10)}`,
  imported: count('imported'), import_rejected: count('import_rejected'), drafted: count('drafted'), disqualified: count('disqualified'),
  research_failed: count('research_failed'), approved: count('approved') + count('approved_with_edits'), rejected: count('rejected'),
  first_touch_sent: sent, followups_sent: fu, replies, reply_rate_pct: sent ? Math.round((replies / sent) * 1000) / 10 : 0,
  reply_categories: replyCats, replies_we_sent: count('reply_sent'), bounced: count('bounced'), unsubscribed: count('unsubscribed'),
  snoozed: count('snoozed'), errors: count('send_failed') + count('followup_failed') + count('reply_failed'), pipeline,
};
return [{ json: { metrics, metrics_text: JSON.stringify(metrics, null, 1).replace(/[{}]/g, ' ') } }];
''', (880, 0))
    llm = chain_llm(wf, 'AI Weekly Insight',
        "=Here are last week's cold outreach numbers for a freelance automation builder:\n{{ $json.metrics_text }}\n\n"
        "Write exactly 3 short lines, plain text, no bullets or numbering: line 1 what happened, line 2 the most important signal (reply rate, bounces, approvals, or quality), "
        "line 3 one concrete action for next week. If volumes are tiny, say so plainly instead of over-interpreting.",
        (1100, 0), 'Gemini (Insight)', temp=0.3)
    rep = codeN(wf, 'Build HTML Report', r'''
const m = $('Compute Metrics').first().json.metrics;
const insight = String($input.first().json.text || '').trim();
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const row = (k, v) => `<tr><td style="padding:4px 12px 4px 0">${esc(k)}</td><td><b>${esc(v)}</b></td></tr>`;
const rows = [['Imported', m.imported], ['Rejected at intake (dupes/suppressed/invalid)', m.import_rejected], ['Drafted', m.drafted], ['Disqualified (not a fit)', m.disqualified],
  ['Research failed', m.research_failed], ['Approved', m.approved], ['Rejected by you', m.rejected], ['First emails sent', m.first_touch_sent],
  ['Follow-ups sent', m.followups_sent], ['Replies', m.replies], ['Reply rate', m.reply_rate_pct + '%'], ['Replies we sent', m.replies_we_sent],
  ['Bounced', m.bounced], ['Unsubscribed', m.unsubscribed], ['Snoozed', m.snoozed], ['Send errors', m.errors]].map(([k, v]) => row(k, v)).join('');
const cats = Object.entries(m.reply_categories).map(([k, v]) => `${esc(k)}: ${v}`).join(', ') || 'none';
const pipe = Object.entries(m.pipeline).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${esc(k)}: ${v}`).join(', ') || 'empty';
const html = `<h2>Outreach weekly report</h2><p>${esc(m.period)}</p>
<p style="background:#f4f6f8;padding:10px;border-radius:6px">${esc(insight || '(insight unavailable)').replace(/\n/g, '<br>')}</p>
<table>${rows}</table><p><b>Reply categories:</b> ${cats}</p><p><b>Pipeline now:</b> ${pipe}</p>`;
return [{ json: { html, subject: `Outreach weekly: ${m.first_touch_sent} sent, ${m.replies} replies (${m.reply_rate_pct}%)`, detail: `sent=${m.first_touch_sent} replies=${m.replies} bounced=${m.bounced}` } }];
''', (1380, 0))
    send = wf.add('Email Report (Gmail)', 'n8n-nodes-base.gmail', 'gmail', {
        'resource': 'message', 'operation': 'send', 'sendTo': "={{ $('Config').first().json.REPORT_EMAIL }}",
        'subject': '={{ $json.subject }}', 'emailType': 'html', 'message': '={{ $json.html }}', 'options': {'appendAttribution': False}}, (1600, 0))
    wf.ext(send, wait=5000)
    sh = codeN(wf, 'Shape: Report Event', r'''
return [{ json: { timestamp: new Date().toISOString(), prospect_id: '', workflow: 'OA-06-weekly-report', event: 'weekly_report_sent', detail: $('Build HTML Report').first().json.detail } }];
''', (1820, 0))
    lg = sheet(wf, 'Log Event', sheets_append('Events'), (2040, 0))
    wf.chain(t, cfg, ev, pr, m, llm, rep, send, sh, lg)
    wf.dump(path)
    import json as _j
    d = _j.load(open(path)); d['settings']['timezone'] = 'Asia/Kolkata'; _j.dump(d, open(path, 'w'), indent=2, ensure_ascii=False)
