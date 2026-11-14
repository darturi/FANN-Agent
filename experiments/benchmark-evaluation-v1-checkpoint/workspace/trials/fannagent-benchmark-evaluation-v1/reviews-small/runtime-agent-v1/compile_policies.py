"""Compile frozen causal JSON branches into the existing shared confirmation path."""
import json,hashlib,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'runtime-parent-v1/engine'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate(policies):
 lines=['/* Generated from frozen model-authored JSON; do not edit thresholds. */', 'static bool CompiledStudyRule(int arm, int filter, int cp, int count, double gap, double tenth, int turnover)', '{','  if (count < 10) return false;']
 names={'qualifying_count':'count','frontier_gap':'gap','tenth_distance':'tenth','top10_new_since_previous':'turnover'}
 for arm,p in enumerate(policies,7):
  for f,clauses in p['rules'].items():
   t=-1 if f=='unfiltered' else int(f[5:])
   for c in clauses:
    parts=[f'arm == {arm}',f'filter == {t}',f'cp == {c["cp"]}']
    for feature,op,value in c['conditions']:
     if feature=='top10_new_since_previous':parts.append('turnover >= 0')
     parts.append(f'{names[feature]} {op} {float(value).hex()}')
    lines.append('  if ('+' && '.join(parts)+') return true;')
 lines+=['  return false;','}'];return '\n'.join(lines)+'\n'
def main():
 data=json.loads((HERE/'eligible-policies.json').read_text());assert len(data['policies'])==3
 (HERE/'engine/src/compiled_study_policies.inc').write_text(generate(data['policies']))
 p=HERE/'engine/src/hnswutils.c';s=(OLD/'src/hnswutils.c').read_text();needle='static bool\nConfirmationRule('
 assert s.count(needle)==1;s=s.replace(needle,'#include "compiled_study_policies.inc"\n\n'+needle)
 old='return ConfirmationRule(arm, checkpoint, frontier - top[9], top[9], turnover);'
 assert s.count(old)==1;s=s.replace(old,'if (arm >= 7) return CompiledStudyRule(arm, FannbenchStudyThreshold(), checkpoint, count, frontier - top[9], top[9], turnover);\n    '+old);p.write_text(s)
 p=HERE/'engine/src/fannbench.c';s=(OLD/'src/fannbench.c').read_text();assert s.count('arm > 6')==1;s=s.replace('arm > 6','arm > 9');s+='\nint\nFannbenchStudyThreshold(void)\n{\n    return studyThreshold;\n}\n';p.write_text(s)
 p=HERE/'engine/src/fannbench.h';p.write_text((OLD/'src/fannbench.h').read_text()+'\nextern int FannbenchStudyThreshold(void);\n')
 changed={}
 for p in OLD.rglob('*'):
  if p.is_file() and p.suffix in ('.c','.h','.inc'):
   q=HERE/'engine'/p.relative_to(OLD)
   if p.read_bytes()!=q.read_bytes():changed[str(p.relative_to(OLD))]={'before':sha(p),'after':sha(q)}
 assert set(changed)=={'src/hnswutils.c','src/fannbench.c','src/fannbench.h'}
 manifest={'eligible_policy_export_sha256':sha(HERE/'eligible-policies.json'),'generated_include_sha256':sha(HERE/'engine/src/compiled_study_policies.inc'),'changes':changed,'arms':{str(i):p for i,p in enumerate(data['policies'],7)},'native_and_legacy_arms_unchanged':True,'graph_changes':False,'compiler':'hexadecimal double literals; unavailable turnover guarded; qualifying_count>=10; fixed filter/checkpoint branches'}
 (HERE/'compiled-policies.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
