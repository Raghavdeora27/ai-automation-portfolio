from common import *

QUALITY_JS = r'''
const BUZZ = ['synergy','leverage','cutting-edge','cutting edge','game-changer','game changer','revolutionize','revolutionise','streamline','ai-powered','seamless','unlock','elevate','robust','innovative','best-in-class','disrupt','supercharge','next-level','paradigm','empower','10x'];
function checkDraft(d, senderName) {
  const body = String(d.body || '').trim();
  const words = body.split(/\s+/).filter(Boolean).length;
  const paras = body.split(/\n\s*\n/).filter(p => p.trim()).length;
  const issues = [];
  if (words < 80 || words > 120) issues.push(`word count ${words} (needs 80-120)`);
  if (paras < 3 || paras > 5) issues.push(`${paras} paragraphs (aim for about 3 short ones plus sign-off)`);
  if (/^\s*([-*\u2022]|\d+[.)])\s+/m.test(body)) issues.push('contains a list');
  if (/^\s*[A-Z][A-Za-z ]{2,20}:\s/m.test(body) && !/^\s*(Hi|Hello|Hey)\b/m.test(body.split('\n')[0] || '')) issues.push('contains a label like "Observation:"');
  const low = body.toLowerCase();
  const buzz = BUZZ.filter(b => low.includes(b));
  if (buzz.length) issues.push('buzzwords: ' + buzz.join(', '));
  if (!/video/i.test(body)) issues.push('missing the soft 2-minute video offer');
  if (senderName && !body.trim().endsWith(senderName)) issues.push(`must end with the signature "${senderName}"`);
  if (/!/.test(body)) issues.push('uses exclamation marks');
  if (!String(d.subject || '').trim()) issues.push('empty subject');
  let score = Math.max(1, Math.min(10, Math.round(Number(d.quality_score) || 0)));
  score = Math.max(1, score - Math.min(4, issues.length * 2));
  return { score, issues, words };
}
'''

DRAFT_SCHEMA = {
    'type': 'object',
    'properties': {
        'fit': {'type': 'boolean', 'description': 'true if this business is a plausible client for small automation work'},
        'fit_reason': {'type': 'string', 'description': 'one sentence explaining the fit decision'},
        'specific_observation': {'type': 'string', 'description': 'the one concrete detail from their website used in the email'},
        'subject': {'type': 'string', 'description': '2-6 word plain subject line'},
        'body': {'type': 'string', 'description': 'plain-text email body, 80-120 words, paragraphs separated by blank lines, signed with the sender name'},
        'quality_score': {'type': 'integer', 'minimum': 1, 'maximum': 10, 'description': 'honest self-rating of specificity and naturalness'},
    },
    'required': ['fit', 'fit_reason', 'specific_observation', 'subject', 'body', 'quality_score'],
}

SYSTEM = (
    "=You are the research and copywriting assistant for {{ $('Config').first().json.SENDER_NAME }}, a freelance automation builder. "
    "What they offer: {{ $('Config').first().json.MY_SERVICE_ONE_LINER }}\n\n"
    "STEP 1 - prior contact: call the prior_messages tool once with the prospect's company domain. If earlier messages exist, do not reuse their angle or subject, and do not mention them.\n\n"
    "STEP 2 - fit: fit is true only for a real, operating small or mid-sized business whose website suggests manual, repetitive work that automation could reduce (enquiries, bookings, quotes, orders, onboarding, follow-ups, reporting). "
    "fit is false for parked, placeholder or example domains, sites with almost no real content, large enterprises, government bodies, and businesses that themselves sell automation. If fit is false still return every field, using short placeholder text for subject and body.\n\n"
    "STEP 3 - the email, plain text only:\n"
    "- 80 to 120 words in about 3 short paragraphs separated by blank lines, then a sign-off.\n"
    "- Open with Hi and the first name.\n"
    "- Exactly one specific observation taken from the website text: a named service, page, booking or enquiry flow, or a phrase they use. No generic praise.\n"
    "- Link that observation to one concrete way an automation could save them time.\n"
    "- Close with a soft, low-pressure offer to send a 2-minute video showing the idea. Do not ask for a call and do not include links.\n"
    "- No bullet points, no numbered lists, no headings or labels, no emojis, no exclamation marks.\n"
    "- Never use buzzwords such as synergy, leverage, cutting-edge, game-changer, revolutionize, streamline, AI-powered, seamless, unlock, elevate, robust, innovative.\n"
    "- Final two lines: Best, then {{ $('Config').first().json.SENDER_NAME }}\n"
    "- Never invent facts that are not in the website text or notes.\n\n"
    "Subject: 2 to 6 plain words, no clickbait, no emojis.\n"
    "quality_score: an honest 1 to 10 rating of how specific, natural and rule-compliant the email is."
)

USER = (
    "=Prospect\nFirst name: {{ $json.first_name }}\nCompany: {{ $json.company }}\nCompany domain: {{ $json.domain }}\n"
    "Website: {{ $json.website }}\nNotes from my CRM: {{ $json.notes }}\n\n"
    "Website text (cleaned, truncated to 6000 characters):\n{{ $json.site_text }}"
)

CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

def build_02(path):
    wf = WF('OA-02 · Research & Draft', '02')
    wf.note('Research & draft (every 30 min)', 'Takes up to **10** prospects with status `new` and a prospect_id, one at a time:\n1. Re-reads the row and locks it as `researching` (idempotent: a row is only processed if it is still `new`)\n2. Fetches the website with a Chrome user-agent (15 s timeout, 3 retries, continue on fail) and strips it to text (6000 chars)\n3. **AI Agent (Gemini)** checks fit, checks prior messages to the same domain via a **Google Sheets tool**, writes the email; Structured Output Parser enforces the JSON. The agent and Gemini nodes retry 4 times, 5 s apart\n4. Code re-scores the draft against the style rules; below MIN_QUALITY gets **one** regenerate\n5. Saves the draft to **Messages**, sets `drafted` / `disqualified` / `research_failed`, logs to **Events**. `research_failed` also appends a row to **Errors** (this caught path does not raise to OA-99)', (-100, -520), 780, 380, 4)
    wf.note('Style rules live in the Agent system prompt', 'Edit **AI Research & Draft Agent → Options → System Message** to change tone. `Score & Check Draft` enforces word count, paragraphs, no lists/labels/buzzwords, video offer and signature in code, so a weak draft is caught even if the model rates itself highly.', (1900, -480), 620, 230, 6)
    t = wf.add('Every 30 min', 'n8n-nodes-base.scheduleTrigger', 'schedule', {'rule': {'interval': [{'field': 'minutes', 'minutesInterval': 30}]}}, (0, 0))
    cfg = config(wf, (220, 0), [('BATCH_SIZE', 10, 'number'), ('MIN_QUALITY', 7, 'number'), ('MAX_SITE_CHARS', 6000, 'number')])
    rd = sheet(wf, 'Read New Prospects', sheets_read('Prospects', [('status', 'new')]), (440, 0))
    has = ifN(wf, 'Has prospect_id?', '$json.prospect_id', (550, 180))
    lim = wf.add('Take Batch of 10', 'n8n-nodes-base.limit', 'limit', {'maxItems': 10}, (660, 0))
    lp = loop(wf, 'Loop Prospects', (880, 0))
    done = wf.add('Batch Done', 'n8n-nodes-base.noOp', 'noop', {}, (1100, -160))
    wf.chain(t, cfg, rd, has)
    wf.c(has, lim, 0)  # rows with no prospect_id are dropped
    wf.chain(lim, lp); wf.c(lp, done, 0)
    P = "$('Loop Prospects').first(1).json"
    rr = reread(wf, 'Re-read Prospect', P + '.prospect_id', (1100, 40))
    wf.c(lp, rr, 1)
    still = ifN(wf, 'Still new?', "$json.status === 'new'", (1320, 40))
    wf.c(rr, still)
    wf.c(still, lp, 1)  # someone else took it -> next
    lock = codeN(wf, 'Shape: Lock Row', r'''
return [{ json: { prospect_id: $json.prospect_id, status: 'researching', updated_at: new Date().toISOString() } }];
''', (1540, 0))
    lockw = sheet(wf, 'Lock as researching', sheets_update('Prospects', 'prospect_id'), (1760, 0))
    wf.c(still, lock, 0); wf.c(lock, lockw)
    http = wf.add('Fetch Website', 'n8n-nodes-base.httpRequest', 'http', {
        'url': "={{ $('Re-read Prospect').first().json.website }}",
        'sendHeaders': True,
        'headerParameters': {'parameters': [
            {'name': 'User-Agent', 'value': CHROME_UA},
            {'name': 'Accept', 'value': 'text/html,application/xhtml+xml'}]},
        'options': {'timeout': 15000, 'redirect': {'redirect': {'maxRedirects': 5}},
                    'response': {'response': {'responseFormat': 'text', 'outputPropertyName': 'html'}}}},
        (1980, 0), onError='continueRegularOutput')
    wf.ext(http, wait=3000)
    wf.c(lockw, http)
    ext = codeN(wf, 'Extract Site Text', r'''
const p = $('Re-read Prospect').first().json;
const CFG = $('Config').first().json;
const r = $input.first().json || {};
let html = typeof r.html === 'string' ? r.html : (typeof r.data === 'string' ? r.data : '');
const fetchError = r.error ? (r.error.message || JSON.stringify(r.error)).slice(0, 300) : '';
const title = (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [,''])[1].trim();
const meta = (html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)/i) || [,''])[1];
let text = html
  .replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ').replace(/<svg[\s\S]*?<\/svg>/gi, ' ')
  .replace(/<!--[\s\S]*?-->/g, ' ')
  .replace(/<\/(p|div|h[1-6]|li|section|article|br|tr)>/gi, '\n').replace(/<[^>]+>/g, ' ')
  .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"').replace(/&[a-z#0-9]+;/gi, ' ')
  .replace(/[{}]/g, ' ')            // braces would break LangChain prompt templates
  .replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
const max = Number(CFG.MAX_SITE_CHARS || 6000);
const site_text = [title && `Title: ${title}`, meta && `Description: ${meta}`, text].filter(Boolean).join('\n').replace(/[{}]/g, ' ').slice(0, max);
const clean = (s) => String(s ?? '').replace(/[{}]/g, ' ');
return [{ json: {
  prospect_id: p.prospect_id, first_name: clean(p.first_name), company: clean(p.company), domain: clean(p.domain),
  website: clean(p.website), notes: clean(p.notes).slice(0, 500), email: p.email,
  site_text, site_ok: site_text.length >= 200, fetch_error: fetchError || (site_text.length < 200 ? 'site returned too little text' : '') } }];
''', (2200, 0))
    wf.c(http, ext)
    ok = ifN(wf, 'Site Text OK?', '$json.site_ok', (2420, 0))
    wf.c(ext, ok)
    agent = wf.add('AI Research & Draft Agent', '@n8n/n8n-nodes-langchain.agent', 'agent', {
        'promptType': 'define', 'text': USER, 'hasOutputParser': True,
        'options': {'systemMessage': SYSTEM, 'maxIterations': 6}},         (2680, -100), onError='continueErrorOutput')
    wf.ext(agent, wait=LLM_WAIT, tries=LLM_TRIES)
    g1 = gemini(wf, 'Gemini (Draft)', (2560, 140), 0.6)
    p1 = parser(wf, 'Parse Draft JSON', DRAFT_SCHEMA, (2880, 140))
    tool = wf.add('prior_messages', 'n8n-nodes-base.googleSheetsTool', 'sheets', {
        'descriptionType': 'manual',
        'toolDescription': 'Look up messages we have already sent or drafted to a company. Input: the company domain, e.g. example.com. Returns earlier rows from the Messages tab (subject, body, status, created_at). Empty result means no prior contact.',
        'operation': 'read', 'documentId': rl_doc(), 'sheetName': rl_sheet('Messages'),
        'filtersUI': {'values': [{'lookupColumn': 'domain', 'lookupValue': "={{ $fromAI('domain', 'company domain to look up, e.g. example.com', 'string') }}"}]},
        'options': {}}, (2720, 140))
    wf.ext(tool)
    wf.c(g1, agent, kind='ai_languageModel'); wf.c(p1, agent, kind='ai_outputParser'); wf.c(tool, agent, kind='ai_tool')
    wf.c(ok, agent, 0)
    fail = codeN(wf, 'Research Failed', r'''
const x = $('Extract Site Text').first().json;
const err = $input.first().json.error;
const reason = x.site_ok ? ('AI step failed: ' + String((err && (err.message || err)) || 'unknown').slice(0, 300)) : ('website fetch failed: ' + x.fetch_error);
return [{ json: { outcome: 'research_failed', fit_reason: reason, observation: '', subject: '', body: '', quality_score: 0, regenerated: false, issues: [] } }];
''', (2900, 260))
    wf.c(ok, fail, 1); wf.c(agent, fail, 1)
    score = codeN(wf, 'Score & Check Draft', QUALITY_JS + PARSE_LLM + r'''
const CFG = $('Config').first().json;
const o = parseLLM($input.first().json);
const fit = o.fit === true || String(o.fit).toLowerCase() === 'true';
const chk = checkDraft(o, CFG.SENDER_NAME);
const min = Number(CFG.MIN_QUALITY || 7);
return [{ json: {
  outcome: fit ? 'drafted' : 'disqualified', fit, fit_reason: String(o.fit_reason || '').slice(0, 500),
  observation: String(o.specific_observation || '').slice(0, 500), subject: String(o.subject || '').trim(), body: String(o.body || '').trim(),
  model_score: Number(o.quality_score) || 0, quality_score: chk.score, issues: chk.issues, words: chk.words,
  needs_regen: fit && chk.score < min, regenerated: false } }];
''', (2980, -100))
    wf.c(agent, score, 0)
    need = ifN(wf, 'Below MIN_QUALITY?', '$json.needs_regen', (3200, -100))
    wf.c(score, need)
    regen = chain_llm(wf, 'AI Regenerate Draft',
        "=Rewrite this cold email so it follows every rule below. Keep the same specific observation unless it is weak.\n\n"
        "Problems found in the first draft: {{ $json.issues.join('; ') || 'reads as generic' }}\n\n"
        "First draft subject: {{ $json.subject.replace(/[{}]/g, ' ') }}\nFirst draft body:\n{{ $json.body.replace(/[{}]/g, ' ') }}\n\n"
        "Prospect first name: {{ $('Extract Site Text').first().json.first_name }} | Company: {{ $('Extract Site Text').first().json.company }}\n"
        "Specific observation: {{ $json.observation.replace(/[{}]/g, ' ') }}\n\n"
        "Rules: 80 to 120 words; about 3 short paragraphs separated by blank lines; open with Hi and the first name; exactly one specific observation; one concrete time-saving idea; "
        "a soft offer to send a 2-minute video, no call request, no links; no lists, no labels, no emojis, no exclamation marks; no buzzwords; "
        "last two lines are Best, and {{ $('Config').first().json.SENDER_NAME }}. Subject 2 to 6 plain words. "
        "Set fit to true, keep fit_reason and specific_observation, and give an honest quality_score.",
        (3440, -240), 'Gemini (Regenerate)', 'Parse Regenerated JSON', DRAFT_SCHEMA, 0.5, on_error='continueErrorOutput')
    wf.c(need, regen, 0)
    pick = codeN(wf, 'Pick Best Draft', QUALITY_JS + PARSE_LLM + r'''
const CFG = $('Config').first().json;
const first = $('Score & Check Draft').first().json;
const o = parseLLM($input.first().json);
const chk = checkDraft(o, CFG.SENDER_NAME);
const second = { ...first, subject: String(o.subject || '').trim(), body: String(o.body || '').trim(),
  observation: String(o.specific_observation || first.observation), model_score: Number(o.quality_score) || 0,
  quality_score: chk.score, issues: chk.issues, words: chk.words };
const best = (o.body && second.quality_score >= first.quality_score) ? second : first;
return [{ json: { ...best, outcome: 'drafted', regenerated: true } }];
''', (3720, -240))
    keep = codeN(wf, 'Keep First Draft', r'''
return [{ json: { ...$('Score & Check Draft').first().json, outcome: 'drafted', regenerated: true, issues: [...$('Score & Check Draft').first().json.issues, 'regenerate failed'] } }];
''', (3720, -60))
    wf.c(regen, pick, 0); wf.c(regen, keep, 1)
    fin = codeN(wf, 'Finalize Outcome', r'''
const j = $input.first().json;
return [{ json: { ...j, prospect_id: $('Shape: Lock Row').first().json.prospect_id } }];
''', (3960, 0))
    wf.c(need, fin, 1); wf.c(pick, fin); wf.c(keep, fin); wf.c(fail, fin)
    caught = codeN(wf, 'Shape: Caught Error Row', r'''
const locked = $('Shape: Lock Row').first().json || {};
const failed = $input.first().json || {};
const site = $('Extract Site Text').isExecuted ? $('Extract Site Text').first().json : {};
const where = site.site_ok ? 'AI Research & Draft Agent' : 'Fetch Website';
const pid = String(locked.prospect_id || '');
const reason = String(failed.fit_reason || 'research failed').slice(0, 1200);
let executionId = '';
let mode = '';
let workflowName = 'OA-02 · Research & Draft';
try {
  if (typeof $workflow !== 'undefined' && $workflow && $workflow.name) workflowName = String($workflow.name);
  if (typeof $execution !== 'undefined' && $execution) {
    executionId = String($execution.id || '');
    mode = String($execution.mode || '');
  }
} catch (e) {}
return [{ json: {
  timestamp: new Date().toISOString(),
  workflow: workflowName,
  node: where,
  error_message: (pid ? pid + ': ' : '') + reason,
  execution_id: executionId,
  execution_url: '',
  mode: mode,
} }];
''', (3180, 460))
    errw = sheet(wf, 'Append to Errors', sheets_append('Errors'), (3420, 460), onError='continueRegularOutput')
    wf.c(fail, caught); wf.c(caught, errw)
    rr2 = reread(wf, 'Re-read Before Save', "$('Finalize Outcome').first().json.prospect_id", (4180, 0))
    held = ifN(wf, 'Lock Still Held?', "$json.status === 'researching'", (4400, 0))
    wf.chain(fin, rr2, held)
    wf.c(held, lp, 1)
    isd = ifN(wf, 'Is Drafted?', "$('Finalize Outcome').first().json.outcome === 'drafted'", (4620, -60))
    wf.c(held, isd, 0)
    sm = codeN(wf, 'Shape: Draft Message', r'''
const f = $('Finalize Outcome').first().json;
const p = $('Re-read Before Save').first().json;
const now = new Date().toISOString();
return [{ json: { message_key: `${p.prospect_id}-initial-${Date.now()}`, prospect_id: p.prospect_id, email: p.email, domain: p.domain,
  kind: 'initial', subject: f.subject, body: f.body, quality_score: f.quality_score, status: 'draft',
  thread_id: '', gmail_message_id: '', created_at: now, sent_at: '' } }];
''', (4840, -160))
    smw = sheet(wf, 'Save Draft to Messages', sheets_append('Messages'), (5060, -160))
    wf.c(isd, sm, 0); wf.c(sm, smw)
    sp = codeN(wf, 'Shape: Prospect Outcome', r'''
const f = $('Finalize Outcome').first().json;
const now = new Date().toISOString();
const detail = f.outcome === 'drafted'
  ? `score ${f.quality_score}/10 (model ${f.model_score}), ${f.words} words${f.regenerated ? ', regenerated once' : ''}${f.issues && f.issues.length ? '; issues: ' + f.issues.join('; ') : ''}`
  : f.fit_reason;
return [{ json: { prospect_id: f.prospect_id, status: f.outcome, fit_reason: f.fit_reason, observation: f.observation,
  updated_at: now, _event: f.outcome, _detail: detail } }];
''', (5280, 0))
    wf.c(smw, sp); wf.c(isd, sp, 1)
    tail = common_tail(wf, 'OA-02-research-draft', 'Loop Prospects', (5500, 0))
    wf.c(sp, tail)
    wf.dump(path)
