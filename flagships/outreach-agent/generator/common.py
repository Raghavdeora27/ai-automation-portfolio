from lib import *

PARSE_LLM = r'''
function parseLLM(j) {
  let o = j && j.output !== undefined ? j.output : j;
  if (o && typeof o.text === 'string' && o.output === undefined && Object.keys(o).length === 1) o = o.text;
  if (typeof o === 'string') {
    const m = o.match(/\{[\s\S]*\}/);
    try { o = JSON.parse(m ? m[0] : o); } catch (e) { o = { _raw: o }; }
  }
  if (o && o.output && typeof o.output === 'object') o = o.output;
  return o || {};
}
'''

def gemini(wf, name, pos, temp=0.5):
    n = wf.add(name, '@n8n/n8n-nodes-langchain.lmChatGoogleGemini', 'gemini',
               {'modelName': GEMINI_MODEL, 'options': {'temperature': temp}}, pos)
    wf.ext(n, wait=4000)
    return n

def parser(wf, name, schema, pos):
    return wf.add(name, '@n8n/n8n-nodes-langchain.outputParserStructured', 'parser',
                  {'schemaType': 'manual', 'inputSchema': json.dumps(schema, indent=2)}, pos)

def chain_llm(wf, name, text, pos, model_name, parser_name=None, schema=None, temp=0.4, on_error=None):
    p = {'promptType': 'define', 'text': text, 'hasOutputParser': bool(schema)}
    extra = {}
    if on_error: extra['onError'] = on_error
    n = wf.add(name, '@n8n/n8n-nodes-langchain.chainLlm', 'chain', p, pos, **extra)
    wf.ext(n, wait=5000)
    g = gemini(wf, model_name, (pos[0] - 40, pos[1] + 200), temp)
    wf.c(g, n, kind='ai_languageModel')
    if schema:
        ps = parser(wf, parser_name, schema, (pos[0] + 140, pos[1] + 200))
        wf.c(ps, n, kind='ai_outputParser')
    return n

def sheet(wf, name, params, pos, **kw):
    n = wf.add(name, 'n8n-nodes-base.googleSheets', 'sheets', params, pos, **kw)
    wf.ext(n)
    return n

def reread(wf, name, pid_expr, pos):
    return sheet(wf, name, sheets_read('Prospects', [('prospect_id', '={{ ' + pid_expr + ' }}')]), pos, alwaysOutputData=True)

def codeN(wf, name, js, pos, **kw):
    return wf.add(name, 'n8n-nodes-base.code', 'code', code(js), pos, **kw)

def ifN(wf, name, expr, pos):
    return wf.add(name, 'n8n-nodes-base.if', 'if_', if_params(expr, wf.key + name), pos)

def switchN(wf, name, rules, pos):
    return wf.add(name, 'n8n-nodes-base.switch', 'switch', switch_params(rules, wf.key + name), pos)

def loop(wf, name, pos):
    return wf.add(name, 'n8n-nodes-base.splitInBatches', 'loop', {'batchSize': 1, 'options': {}}, pos)

def config(wf, pos, extra=None):
    return wf.add('Config', 'n8n-nodes-base.set', 'set', config_params(extra), pos)

def common_tail(wf, workflow_tag, loop_name, pos):
    """Update Prospect (by prospect_id) -> Build Event Row -> Log Event -> back to loop. Returns entry node."""
    up = sheet(wf, 'Update Prospect', sheets_update('Prospects', 'prospect_id'), pos)
    ev = codeN(wf, 'Build Event Row', r'''
return $input.all().map(i => ({ json: {
  timestamp: new Date().toISOString(), prospect_id: i.json.prospect_id || '', workflow: '%s',
  event: i.json._event || 'updated', detail: String(i.json._detail || '').slice(0, 900) } }));
''' % workflow_tag, (pos[0] + 220, pos[1]))
    lg = sheet(wf, 'Log Event', sheets_append('Events'), (pos[0] + 440, pos[1]))
    wf.chain(up, ev, lg)
    if loop_name: wf.c(lg, loop_name)
    return up

def strip_prospect(js_obj_expr):
    return js_obj_expr
