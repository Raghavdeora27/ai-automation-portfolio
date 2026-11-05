import json, uuid, hashlib

V = dict(  # typeVersions used on self-hosted n8n 2.8.4
    form='2.2', formPage='2.3', execWf='1.2', execWfTrigger='1.1', webhook='2', respond='1.1', schedule='1.2', set='3.4', code='2', if_='2.2', switch='3.2',
    sheets='4.5', gmail='2.1', gmailTrigger='1.2', http='4.2', limit='1', loop='3', errorTrigger='1',
    sticky='1', noop='1', agent='2.2', chain='1.5', gemini='1', parser='1.2')
def num(v): return float(v) if '.' in v else int(v)

GEMINI_MODEL = 'models/gemini-3.5-flash-lite'
LLM_TRIES = 4
LLM_WAIT = 5000

def uid(seed):
    return str(uuid.UUID(hashlib.md5(seed.encode()).hexdigest()))

class WF:
    def __init__(self, name, key):
        self.name, self.key = name, key
        self.nodes, self.conns = [], {}
    def add(self, name, type_, ver, params, pos, **extra):
        assert all(n['name'] != name for n in self.nodes), name
        n = {'parameters': params, 'id': uid(self.key + name), 'name': name, 'type': type_,
             'typeVersion': num(V[ver]) if ver in V else num(ver), 'position': [int(pos[0]), int(pos[1])]}
        n.update(extra)
        self.nodes.append(n)
        return name
    def ext(self, name, retry=True, wait=3000, tries=3):
        """mark external-call node with retries. Sheets, Gmail and HTTP stay at 3 tries.
        Gemini and the agent/chain nodes pass tries=4 and wait=5000."""
        for n in self.nodes:
            if n['name'] == name:
                n['retryOnFail'] = True; n['maxTries'] = tries; n['waitBetweenTries'] = wait
        return name
    def c(self, a, b, out=0, inp=0, kind='main'):
        self.conns.setdefault(a, {}).setdefault(kind, [])
        lst = self.conns[a][kind]
        while len(lst) <= out: lst.append([])
        lst[out].append({'node': b, 'type': kind, 'index': inp})
    def chain(self, *names):
        for a, b in zip(names, names[1:]): self.c(a, b)
    def note(self, title, text, pos, w=460, h=300, color=7):
        name = 'Note: ' + title
        self.add(name, 'n8n-nodes-base.stickyNote', 'sticky',
                 {'content': f'## {title}\n{text}', 'height': h, 'width': w, 'color': color}, pos)
    def dump(self, path, error_wf=True, timezone=None):
        settings = {'executionOrder': 'v1', 'saveDataErrorExecution': 'all', 'saveDataSuccessExecution': 'all',
                    'saveManualExecutions': True, 'callerPolicy': 'workflowsFromSameOwner'}
        if error_wf: settings['errorWorkflow'] = 'REPLACE_WITH_OA99_ERROR_HANDLER_WORKFLOW_ID'
        if timezone: settings['timezone'] = timezone
        wf = {'name': self.name, 'nodes': self.nodes, 'connections': self.conns, 'settings': settings,
              'pinData': {}, 'active': False, 'meta': {'templateCredsSetupCompleted': False}}
        with open(path, 'w') as f: json.dump(wf, f, indent=2, ensure_ascii=False)

# ---------- parameter builders ----------
def rl_doc():
    return {'__rl': True, 'value': "={{ $('Config').first().json.SHEET_ID }}", 'mode': 'id'}
def rl_sheet(tab):
    return {'__rl': True, 'value': tab, 'mode': 'name'}

def sheets_read(tab, filters=None):
    p = {'operation': 'read', 'documentId': rl_doc(), 'sheetName': rl_sheet(tab)}
    if filters:
        p['filtersUI'] = {'values': [{'lookupColumn': k, 'lookupValue': v} for k, v in filters]}
        p['combineFilters'] = 'AND'
    p['options'] = {}
    return p
def sheets_append(tab):
    return {'operation': 'append', 'documentId': rl_doc(), 'sheetName': rl_sheet(tab),
            'columns': {'mappingMode': 'autoMapInputData', 'value': {}, 'matchingColumns': [], 'schema': []},
            'options': {'cellFormat': 'RAW', 'handlingExtraData': 'ignoreIt'}}
def sheets_update(tab, key):
    return {'operation': 'update', 'documentId': rl_doc(), 'sheetName': rl_sheet(tab),
            'columns': {'mappingMode': 'autoMapInputData', 'value': {}, 'matchingColumns': [key], 'schema': []},
            'options': {'cellFormat': 'RAW', 'handlingExtraData': 'ignoreIt'}}

def cond_bool(expr, cid):
    return {'id': uid(cid), 'leftValue': '={{ ' + expr + ' }}', 'rightValue': '',
            'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}
def if_params(expr, cid):
    return {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose', 'version': 2},
                           'conditions': [cond_bool('Boolean(' + expr + ')', cid)], 'combinator': 'and'},
            'looseTypeValidation': True, 'options': {}}
def switch_params(rules, cid):
    vals = []
    for key, expr in rules:
        vals.append({'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose', 'version': 2},
                                    'conditions': [cond_bool('Boolean(' + expr + ')', cid + key)], 'combinator': 'and'},
                     'renameOutput': True, 'outputKey': key})
    return {'rules': {'values': vals}, 'looseTypeValidation': True, 'options': {}}

def code(js, each=False):
    p = {'jsCode': js.strip()}
    if each: p['mode'] = 'runOnceForEachItem'
    return p

def config_params(extra=None, include_other=False):
    base = [
        ('SHEET_ID', 'YOUR_GOOGLE_SHEET_ID', 'string'),
        ('SENDER_NAME', 'Raghav', 'string'),
        ('SENDER_EMAIL', 'you@yourdomain.com', 'string'),
        ('APPROVER_EMAIL', 'approver@yourdomain.com', 'string'),
        ('ALERT_EMAIL', 'alerts@yourdomain.com', 'string'),
        ('DAILY_CAP', 30, 'number'),
        ('DEFAULT_TIMEZONE', 'Asia/Kolkata', 'string'),
        ('SEND_WINDOW_START_HOUR', 9, 'number'),
        ('SEND_WINDOW_END_HOUR', 17, 'number'),
        ('IGNORE_SEND_WINDOW', False, 'boolean'),
        ('FOLLOWUP_1_DELAY_BUSINESS_DAYS', 3, 'number'),
        ('FOLLOWUP_2_DELAY_BUSINESS_DAYS', 4, 'number'),
        ('TEST_FOLLOWUP_DELAY_MINUTES', 0, 'number'),
        ('MY_SERVICE_ONE_LINER', 'I build small automations that take repetitive admin (follow-ups, bookings, data entry) off a business owner\'s plate.', 'string'),
    ]
    rows = base + (extra or [])
    p = {'assignments': {'assignments': [
        {'id': uid('cfg' + k), 'name': k, 'value': v, 'type': t} for k, v, t in rows]}}
    if include_other: p['includeOtherFields'] = True
    p['options'] = {}
    return p

# ---------- shared JS ----------
JS_HELPERS = r'''
const CFG = $('Config').first().json;
const nowIso = () => new Date().toISOString();
const lc = (s) => String(s ?? '').trim().toLowerCase();
function zoneFor(tz) {
  const z = String(tz || '').trim();
  if (z && DateTime.now().setZone(z).isValid) return z;
  return CFG.DEFAULT_TIMEZONE || 'UTC';
}
function addBusinessDays(dt, n) {
  let d = dt; let added = 0;
  while (added < n) { d = d.plus({ days: 1 }); if (d.weekday <= 5) added++; }
  return d;
}
function nextFollowupIso(businessDays, tz) {
  const testMin = Number(CFG.TEST_FOLLOWUP_DELAY_MINUTES || 0);
  if (testMin > 0) return DateTime.utc().plus({ minutes: testMin }).toISO();
  return addBusinessDays(DateTime.now().setZone(zoneFor(tz)), Number(businessDays)).toUTC().toISO();
}
function sendWindow(tz) {
  const zone = zoneFor(tz);
  const local = DateTime.now().setZone(zone);
  if (CFG.IGNORE_SEND_WINDOW === true || String(CFG.IGNORE_SEND_WINDOW).toLowerCase() === 'true') {
    return { ok: true, zone, local: local.toFormat('ccc HH:mm') };
  }
  const ok = local.weekday <= 5 && local.hour >= Number(CFG.SEND_WINDOW_START_HOUR ?? 9) && local.hour < Number(CFG.SEND_WINDOW_END_HOUR ?? 17);
  return { ok, zone, local: local.toFormat('ccc HH:mm') };
}
function rowsOf(nodeName) {
  try { return $(nodeName).all().map(i => i.json).filter(r => r && Object.keys(r).length); } catch (e) { return []; }
}
function sentTodayCount(eventRows) {
  const zone = zoneFor(CFG.DEFAULT_TIMEZONE);
  const today = DateTime.now().setZone(zone).toISODate();
  return eventRows.filter(r => ['sent', 'followup_sent', 'reply_sent'].includes(lc(r.event)) && r.timestamp &&
    DateTime.fromISO(String(r.timestamp)).setZone(zone).toISODate() === today).length;
}
function isSuppressed(email, domain, suppRows) {
  const e = lc(email); const d = lc(domain);
  return suppRows.some(r => (lc(r.email) && lc(r.email) === e) || (!lc(r.email) && lc(r.domain) && lc(r.domain) === d));
}
const safe = (s) => String(s ?? '').replace(/[{}]/g, ' ');
'''
