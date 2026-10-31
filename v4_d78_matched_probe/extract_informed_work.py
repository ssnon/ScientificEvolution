#!/usr/bin/env python3
"""Read-only exact model/tool evidence extraction for a selected research Work."""
import argparse,json
from pathlib import Path
from e2core.core import EvolutionJournal,sha,canon,guard

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--work-id',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    root=a.root.expanduser().resolve(strict=True)
    out=a.out.expanduser().absolute()
    guard(out.parent.is_dir() and not out.exists(),'OUTPUT_MUST_BE_NEW')
    j=EvolutionJournal(root)
    s=j.verify()
    guard(a.work_id in s.work,'UNKNOWN_WORK_ID')
    w=s.work[a.work_id]
    steps=[]
    for st in w['steps']:
        data=json.loads(j.raw(st['raw_blob']))
        steps.append({'step':st['step'],'kind':st['kind'],'content':data,
                      'raw_blob_sha256':st['raw_blob']})
    tools=[]
    for ident,tool in s.tool_results.items():
        if tool.get('work_id')==a.work_id:
            tools.append({'id':ident,'request':json.loads(j.raw(tool['request_blob'])),
                          'result':json.loads(j.raw(tool['result_blob'])),
                          'request_sha256':tool['request_blob'],'result_sha256':tool['result_blob']})
    assets=[]
    for ident in w.get('published',[]):
        rec=s.assets[ident]
        assets.append({'asset':rec,'source_details':[
            {'id':sid,'kind':s.sources[sid]['kind'],'description':s.sources[sid].get('description'),
             'blob_sha256':s.sources[sid]['blob']}
            for sid in rec.get('source_ids',[]) if sid in s.sources]})
    report={
        'root':str(root),'work_id':a.work_id,'work':w,'steps':steps,'tools':tools,'assets':assets,
        'exact_journal_head_sha256':sha(canon(j._events()[-1])),
        'read_only':True,'model_outputs_are_not_independently_verified_science':True,
    }
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({'saved':str(out),'steps':len(steps),'tool_calls':len(tools),
                      'assets':len(assets)},ensure_ascii=False))
if __name__=='__main__':main()
