"""Evidence gate: select -> context -> probe -> failures -> checkpoint.
No arbitrary shell task execution and no game-runtime dependency.
"""
import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from schemas.validate import contract
ROOT=Path(__file__).resolve().parents[1]

def write_json(path, data):
    Path(path).write_text(json.dumps(data,indent=2)+'\n')

def source_hash():
    digest=hashlib.sha256()
    files=[]
    for folder in ('server','client','schemas','storage','tests','harness','fixtures'):
        files.extend(p for p in Path(folder).rglob('*') if p.suffix in ('.py','.js','.css','.html','.json','.jsonl') and '__pycache__' not in str(p) and p.name not in ('context.json','checkpoints.jsonl','tasks.json'))
    for path in sorted(files):digest.update(str(path).encode()+path.read_bytes())
    return digest.hexdigest()

def select_task(tasks):
    done={t['id'] for t in tasks if t['status']=='done'}
    return next((t for t in tasks if t['status']!='done' and set(t['depends'])<=done),None)

def main():
    checks=[]
    def check(name,fn):
        try:
            detail=fn() or 'passed'
            checks.append({'name':name,'passed':True,'detail':str(detail)[-5000:]})
        except Exception as exc:
            checks.append({'name':name,'passed':False,'detail':str(exc)[-5000:]})
    def command(args):
        r=subprocess.run(args,capture_output=True,text=True,timeout=120)
        if r.returncode:raise ValueError((r.stdout+r.stderr)[-5000:])
        return (r.stdout+r.stderr)[-5000:]
    requirements=json.loads(Path('harness/requirements.json').read_text())
    tasks=json.loads(Path('harness/tasks.json').read_text())
    def controls():
        contract('requirements',requirements);contract('tasks',tasks)
        for f in ('PRODUCT.md','ARCHITECTURE.md','BACKLOG.md','DECISIONS.md','EVIDENCE.md'):
            if not Path(f).is_file():raise ValueError('missing '+f)
        req_ids={r['id'] for r in requirements['requirements']}
        ids={t['id'] for t in tasks['tasks']}
        for task in tasks['tasks']:
            if not set(task['requirements'])<=req_ids or not set(task['depends'])<=ids:raise ValueError('dangling task reference '+task['id'])
        for req in requirements['requirements']:
            if not req['tests'] or not req['threshold']:raise ValueError('requirement without evidence mapping')
        return 'All control contracts and task/requirement references valid'
    check('controls',controls)
    def boundaries():
        for path in Path('server').glob('*.py'):
            tree=ast.parse(path.read_text())
            imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            if any(m and m.split('.')[0] in ('harness','evals','tests') for m in imports):raise ValueError('runtime imports development layer')
        tree=ast.parse(Path('server/engine.py').read_text())
        names=[a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
        if set(names)&{'time','socket','urllib','sqlite3','random','os'}:raise ValueError('engine has forbidden I/O dependency')
        return 'Runtime/development boundary and deterministic engine imports checked'
    check('architecture',boundaries)
    check('unit_integration',lambda:command([sys.executable,'-m','unittest','discover','-s','tests','-v']))
    check('client_syntax',lambda:command(['node','--check','client/app.js']))
    check('browser_e2e',lambda:command([sys.executable,'tests/browser_e2e.py']))
    # Requirement evidence is check-bound, not a subjective score.
    passed=all(c['passed'] for c in checks)
    report={'passed':passed,'score':round(100*sum(c['passed'] for c in checks)/len(checks)),'checks':checks}
    contract('evaluation',report)
    write_json('evals/latest.json',report)
    stamp=datetime.now(timezone.utc).isoformat()
    with open('evals/history.jsonl','a') as f:f.write(json.dumps({'at':stamp,**report})+'\n')
    for c in checks:
        if c['passed']:continue
        tid='FIX-'+c['name']
        if not any(t['id']==tid for t in tasks['tasks']):
            tasks['tasks'].append({'id':tid,'objective':'Resolve evaluation failure: '+c['name'],'status':'todo','depends':[],'requirements':['R07','R08'],'validation':['python3 -m harness.run']})
    for task in tasks['tasks']:
        if task['id'].startswith('FIX-'):
            match=next((c for c in checks if task['id']=='FIX-'+c['name']),None)
            if match:task['status']='done' if match['passed'] else 'blocked' if 'Operation not permitted' in match['detail'] else 'todo'
    contract('tasks',tasks);write_json('harness/tasks.json',tasks)
    next_task=select_task(tasks['tasks'])
    context={'objective':next_task['objective'] if next_task else 'All evaluated tasks complete', 'requirements':[r['id']+': '+r['description'] for r in requirements['requirements'] if not next_task or r['id'] in next_task['requirements']], 'interfaces':['schemas/action.json','schemas/telemetry.json','POST /api/chat','GET /api/state'], 'decisions':['Python stdlib + SQLite; no runtime downloads','Providers propose; engine validates; fixed 20/5 clock','Offline fixture cannot invoke live providers'], 'failures':[c['name']+': '+c['detail'][-800:] for c in checks if not c['passed']], 'validation':next_task['validation'] if next_task else ['python3 -m harness.run'],'provenance':'evals/latest.json; source SHA-256 '+source_hash()}
    contract('context',context);write_json('harness/context.json',context)
    checkpoint={'id':stamp,'passed':passed,'source_hash':source_hash(),'evaluation_hash':hashlib.sha256(Path('evals/latest.json').read_bytes()).hexdigest(),'context':'harness/context.json'}
    contract('checkpoint',checkpoint)
    with open('harness/checkpoints.jsonl','a') as f:f.write(json.dumps(checkpoint)+'\n')
    lines=['# Backlog','', 'Order is priority. A failed/blocked release check is never marked complete.','', '| Task | Status | Dependencies | Objective | Validation |','|---|---|---|---|---|']
    lines += [f"| {t['id']} | {t['status']} | {', '.join(t['depends']) or 'none'} | {t['objective']} | {'; '.join(t['validation'])} |" for t in tasks['tasks']]
    Path('BACKLOG.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if passed else 1

if __name__=='__main__':sys.exit(main())
