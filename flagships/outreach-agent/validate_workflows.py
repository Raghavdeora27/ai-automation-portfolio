#!/usr/bin/env python3
"""Static validator for the OA (Outreach Agent) n8n workflows.
Usage: python3 validate_workflows.py [workflows_dir] [n8n_install_dir ...]
Checks: JSON parses; unique node names/ids; connection targets exist; node types + typeVersions exist in the
installed n8n node catalogue; parameter names exist in the node description (recursively for collections);
AI sub-nodes are wired with ai_languageModel / ai_outputParser / ai_tool; every $('Node') reference exists;
external nodes retry (3 tries, 2-5 s); Config node present (when used); Form Trigger never reaches Respond to Webhook; Execute Workflow has a workflowId; errorWorkflow placeholder set; Code nodes compile
(node --check); no secret-looking strings."""
import json, os, re, subprocess, sys, tempfile, glob

WF_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflows')
INSTALLS = sys.argv[2:] or ['/home/box/n8n1', '/home/box/n8n2']
EXTERNAL = {'n8n-nodes-base.googleSheets', 'n8n-nodes-base.gmail', 'n8n-nodes-base.httpRequest', 'n8n-nodes-base.gmailTrigger',
            '@n8n/n8n-nodes-langchain.lmChatGoogleGemini', '@n8n/n8n-nodes-langchain.agent', '@n8n/n8n-nodes-langchain.chainLlm',
            'n8n-nodes-base.googleSheetsTool'}
AI_KIND = {'@n8n/n8n-nodes-langchain.lmChatGoogleGemini': 'ai_languageModel',
           '@n8n/n8n-nodes-langchain.outputParserStructured': 'ai_outputParser',
           'n8n-nodes-base.googleSheetsTool': 'ai_tool'}
SECRET_RE = re.compile(r'(AIza[0-9A-Za-z_\-]{30,}|ya29\.[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN|GOCSPX-|xox[bp]-)')

def load_catalog(install):
    cat = {}
    for f in glob.glob(f'{install}/node_modules/n8n-nodes-base/dist/types/nodes.json') + \
             glob.glob(f'{install}/node_modules/@n8n/n8n-nodes-langchain/dist/types/nodes.json'):
        for d in json.load(open(f)):
            vers = d['version'] if isinstance(d['version'], list) else [d['version']]
            pkg = '@n8n/n8n-nodes-langchain' if 'langchain' in f else 'n8n-nodes-base'
            name = d['name'] if '.' in d['name'] else f'{pkg}.{d["name"]}'
            cat.setdefault(name, []).append((vers, d))
    return cat

def props_for(cat, type_, ver):
    if type_.endswith('Tool') and type_ not in cat:
        type_ = type_[:-4]
    out = []
    for vers, d in cat.get(type_, []):
        if any(abs(float(v) - float(ver)) < 1e-9 for v in vers):
            out += d.get('properties', [])
    return out

def check_value(val, props, path, errs):
    """val: dict of params; props: list of property descriptions that may apply."""
    by = {}
    for p in props: by.setdefault(p['name'], []).append(p)
    for k, v in val.items():
        if k not in by:
            errs.append(f'unknown parameter "{path}{k}"'); continue
        for p in by[k][:1] if len({pp.get('type') for pp in by[k]}) == 1 else []:
            t = p.get('type')
            if t == 'collection' and isinstance(v, dict):
                opts = [o for pp in by[k] for o in pp.get('options', [])]
                check_value(v, opts, f'{path}{k}.', errs)
            elif t == 'fixedCollection' and isinstance(v, dict):
                groups = {o['name']: o for pp in by[k] for o in pp.get('options', [])}
                for gk, gv in v.items():
                    if gk not in groups: errs.append(f'unknown fixedCollection group "{path}{k}.{gk}"'); continue
                    inner = groups[gk].get('values', [])
                    for entry in (gv if isinstance(gv, list) else [gv]):
                        if isinstance(entry, dict): check_value(entry, inner, f'{path}{k}.{gk}.', errs)

def code_ok(js, name):
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write('const $ = () => ({}); const $input = {}; const $json = {}; const DateTime = {};\n(async () => {\n' + js + '\n})();\n')
    r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True)
    os.unlink(f.name)
    return r.returncode == 0, r.stderr.strip().splitlines()[-1:] if r.returncode else ''

def validate(path, cats):
    errs, warns = [], []
    try: wf = json.load(open(path))
    except Exception as e: return [f'JSON parse error: {e}'], []
    nodes = wf.get('nodes', []); names = [n['name'] for n in nodes]
    by = {n['name']: n for n in nodes}
    if len(set(names)) != len(names): errs.append('duplicate node names')
    if len({n['id'] for n in nodes}) != len(nodes): errs.append('duplicate node ids')
    uses_cfg = "$('Config')" in json.dumps(wf) or any(n['type'] in EXTERNAL for n in nodes)
    if uses_cfg and 'Config' not in by: errs.append('missing Config node')
    if not os.path.basename(path).replace('OA-', '', 1).startswith('99') and not wf.get('settings', {}).get('errorWorkflow'):
        errs.append('settings.errorWorkflow placeholder missing')
    for src, kinds in wf.get('connections', {}).items():
        if src not in by: errs.append(f'connection from missing node "{src}"')
        for kind, outs in kinds.items():
            for out in outs:
                for c in out or []:
                    if c['node'] not in by: errs.append(f'connection {src} -> missing "{c["node"]}"')
                    if c['type'] != kind: errs.append(f'connection type mismatch {src}->{c["node"]}')
                    st = by.get(src, {}).get('type')
                    if st in AI_KIND and kind != AI_KIND[st]: errs.append(f'{src} must connect via {AI_KIND[st]}, not {kind}')
                    if kind.startswith('ai_') and by.get(c['node'], {}).get('type') not in (
                        '@n8n/n8n-nodes-langchain.agent', '@n8n/n8n-nodes-langchain.chainLlm'):
                        errs.append(f'AI connection into non-AI root node {c["node"]}')
                    if st not in AI_KIND and kind != 'main': errs.append(f'{src} uses unexpected connection {kind}')
    # n8n Form Trigger (v2.2+) refuses to run if any Respond to Webhook node is downstream of it
    children = {}
    for src, kinds in wf.get('connections', {}).items():
        for outs in kinds.values():
            for out in outs:
                for c in out or []: children.setdefault(src, set()).add(c['node'])
    for n in nodes:
        if n['type'] == 'n8n-nodes-base.formTrigger':
            seen, todo = set(), [n['name']]
            while todo:
                x = todo.pop()
                for ch in children.get(x, ()):
                    if ch not in seen: seen.add(ch); todo.append(ch)
            bad = [x for x in seen if by.get(x, {}).get('type') == 'n8n-nodes-base.respondToWebhook']
            if bad: errs.append(f'Form Trigger "{n["name"]}" reaches Respond to Webhook node(s) {bad} (unsupported in n8n)')
        if n['type'] == 'n8n-nodes-base.executeWorkflow' and n['parameters'].get('source', 'database') == 'database':
            wid = n['parameters'].get('workflowId')
            if not (isinstance(wid, dict) and wid.get('value')) and not (isinstance(wid, str) and wid):
                errs.append(f'{n["name"]}: Execute Workflow has no workflowId')
    # sub-nodes must be connected
    for n in nodes:
        if n['type'] in AI_KIND and n['name'] not in wf['connections']: errs.append(f'AI sub-node {n["name"]} not connected')
    # every AI root has a model
    for n in nodes:
        if n['type'] in ('@n8n/n8n-nodes-langchain.agent', '@n8n/n8n-nodes-langchain.chainLlm'):
            kinds = [k for s, ks in wf['connections'].items() for k, outs in ks.items() for out in outs for c in out if c['node'] == n['name']]
            if 'ai_languageModel' not in kinds: errs.append(f'{n["name"]} has no language model')
            if n['parameters'].get('hasOutputParser') and 'ai_outputParser' not in kinds: errs.append(f'{n["name"]} expects an output parser')
    s = json.dumps(wf)
    for ref in set(re.findall(r"\$\('([^']+)'\)", s)):
        if ref not in by: errs.append(f'expression references missing node "{ref}"')
    if SECRET_RE.search(s): errs.append('secret-looking string found')
    if '"credentials"' in s: errs.append('credentials embedded')
    for n in nodes:
        t, v = n['type'], n['typeVersion']
        if t == 'n8n-nodes-base.stickyNote': continue
        for inst, cat in cats.items():
            base = t[:-4] if t.endswith('Tool') and t not in cat else t
            vers = [x for vs, _ in cat.get(base, []) for x in vs]
            if not vers: errs.append(f'[{inst}] unknown node type {t}')
            elif not any(abs(float(x) - float(v)) < 1e-9 for x in vers): errs.append(f'[{inst}] {t} has no version {v} (has {vers})')
            else:
                pe = []
                extra_ok = {'descriptionType', 'toolDescription'} if t.endswith('Tool') else set()
                check_value({k: x for k, x in n['parameters'].items() if k not in extra_ok}, props_for(cat, t, v), '', pe)
                errs += [f'[{inst}] {n["name"]}: {e}' for e in pe]
        if t in EXTERNAL:
            if not (n.get('retryOnFail') and n.get('maxTries') == 3 and 2000 <= n.get('waitBetweenTries', 0) <= 5000):
                errs.append(f'{n["name"]}: external node without retry 3x / 2-5s')
        if t == 'n8n-nodes-base.code':
            ok, msg = code_ok(n['parameters']['jsCode'], n['name'])
            if not ok: errs.append(f'Code syntax error in {n["name"]}: {msg}')
        if t in ('n8n-nodes-base.gmail',) and n['parameters'].get('operation') == 'sendAndWait' and not n.get('webhookId'):
            errs.append(f'{n["name"]}: sendAndWait needs webhookId')
    return errs, warns

def main():
    cats = {os.path.basename(i): load_catalog(i) for i in INSTALLS if os.path.isdir(i)}
    if not cats: print('WARNING: no n8n install found - type/version/parameter checks skipped')
    files = sorted(glob.glob(os.path.join(WF_DIR, '*.json')))
    bad = 0
    for f in files:
        errs, _ = validate(f, cats)
        wf = json.load(open(f))
        print(f'{"OK  " if not errs else "FAIL"} {os.path.basename(f)}  ({len(wf["nodes"])} nodes)')
        for e in errs: print('     -', e)
        bad += bool(errs)
    print(f'\n{len(files) - bad}/{len(files)} workflows passed; catalogues: {", ".join(cats) or "none"}')
    sys.exit(1 if bad else 0)

if __name__ == '__main__': main()
