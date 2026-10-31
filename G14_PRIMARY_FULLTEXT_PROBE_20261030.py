#!/usr/bin/env python3
"""Read-only, no-model-call primary-literature access probe for G14.

The public HTTP access calls are made via the project's own native
`e2core.research_literature.research_literature` action. Results are saved
OUTSIDE the Journal, are NOT scientific certifications, and are NOT silently
injected into an autonomous Work.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

FIXED_PREFIX_EVENTS = 1182
FIXED_PREFIX_SHA = '0fc0fd99a8564fd8e89b7237617eb1e75181ce09aa1064ace14c2fa0dcf31acf'
PAPERS = [
    {'pmcid':'PMC13325844','doi':'10.1021/acsnano.6c03605',
     'title':'How the Electrochemical Double Layer Manipulates Molecule–Metal Interactions'},
    {'pmcid':'PMC12285619','doi':'10.1002/smtd.202402107',
     'title':'Nanolaminate Nano-Optoelectrodes Enable Dual-Channel Plasmon-Enhanced Raman Spectroscopy for Electrochemistry'},
]


def verify_population(exp):
    import population_run as pop
    import persistent_population as pp
    root = exp / 'CYCLE_014' / 'POPULATION'
    assert (exp/'STOP_REQUESTED').is_file(), 'OPERATOR_STOP_MARKER_REQUIRED'
    mods = pop.gen.modules()
    j,s = pop.root_status(mods, root)
    rows = j._events()
    assert len(rows) >= FIXED_PREFIX_EVENTS, 'BEFORE_G14_1182_CHECKPOINT'
    assert mods.sha(mods.canon(rows[FIXED_PREFIX_EVENTS-1])) == FIXED_PREFIX_SHA, 'IMMUTABLE_PREFIX_MISMATCH'
    assert 'W_P0_primary_sers_precedent_retrieval_002' in s.work, 'LITERATURE_WORK_NOT_FOUND'
    assert all(c['state']=='SAVED' for c in s.model_calls.values()), 'UNCERTAIN_PROVIDER_CALL'
    return mods, pp.digest(mods,j),s.work['W_P0_primary_sers_precedent_retrieval_002']['status']


def summarize_result(result):
    if not isinstance(result,dict):
        return {'status':'INVALID_RESULT','detail':str(type(result))}
    return {k:result.get(k) for k in ('status','action','error_code','evidence_class','pmcid',
               'source_url','source_sha256','paragraph_count','next_offset',
               'supplement_contents_retrieved','source_id') if k in result}


def probe_one(paper,max_pages,include_supplements,native):
    pmcid=paper['pmcid']
    rows=[];steps=[];errors=[]
    for i in range(max_pages):
        args={'action':'read_fulltext','pmcid':pmcid,'offset':i*8,'limit':8}
        out=native(args)
        steps.append({'arguments':args,'response':out})
        if out.get('status')!='DELIVERED' or out.get('evidence_class')!='OA_FULLTEXT_TEXT':
            errors.append({'action':'read_fulltext','page_index':i,'diagnostic':summarize_result(out)})
            break
        rows.extend(out.get('paragraphs',[]))
        if out.get('next_offset') is None:break
    captions=native({'action':'figure_captions','pmcid':pmcid})
    steps.append({'arguments':{'action':'figure_captions','pmcid':pmcid},'response':captions})
    supplement_index=native({'action':'supplement_files','pmcid':pmcid}) if include_supplements else None
    if supplement_index is not None:
        steps.append({'arguments':{'action':'supplement_files','pmcid':pmcid},'response':supplement_index})
        # The optional index is not itself supporting-information evidence.
        entries=supplement_index.get('archive_entries',[]) if isinstance(supplement_index,dict) else []
        # Only one safely indexed file and one PDF page; no claim of exhaustive SI inspection.
        if supplement_index.get('status')=='DELIVERED' and entries:
            index=entries[0]['file_index']
            args={'action':'supplement_files','pmcid':pmcid,'file_index':index,'page':1}
            extracted=native(args)
            steps.append({'arguments':args,'response':extracted})
    return {'paper':paper,'fulltext_paragraphs_retrieved':len(rows),
            'fulltext_access_confirmed':bool(rows),
            'figure_captions_retrieved':captions.get('status')=='DELIVERED',
            'supplement_text_retrieved':any(s['response'].get('status')=='DELIVERED' and
                s['response'].get('evidence_class')=='OA_SUPPLEMENT_TEXT' for s in steps),
            'errors':errors,'steps':steps}


def selftest():
    assert len(PAPERS)==2 and all(p['pmcid'].startswith('PMC') for p in PAPERS)
    x=summarize_result({'status':'DELIVERED','action':'read_fulltext','evidence_class':'OA_FULLTEXT_TEXT', 'paragraphs':[1]})
    assert x=={'status':'DELIVERED','action':'read_fulltext','evidence_class':'OA_FULLTEXT_TEXT'}
    called=[]
    def fake(args):
        called.append(args)
        if args['action']=='read_fulltext':
            return {'status':'DELIVERED','action':'read_fulltext','evidence_class':'OA_FULLTEXT_TEXT','paragraphs':[{'index':0,'text':'Mock paragraph'}], 'next_offset':None}
        if args['action']=='figure_captions':return {'status':'DELIVERED','captions':[]}
        if args['action']=='supplement_files':return {'status':'DELIVERED','archive_entries':[]}
        raise AssertionError('UNEXPECTED_ACTION')
    r=probe_one(PAPERS[0],2,True,fake)
    assert r['fulltext_paragraphs_retrieved']==1 and r['figure_captions_retrieved']
    assert len(called)==3
    print(json.dumps({'status':'G14_FREE_PRIMARY_PROBE_SELFTEST_OK','checks':5,
                      'provider_requests_sent':0,'journal_modified':False}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['selftest','probe'])
    p.add_argument('--experiment',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--max-pages',type=int,default=3,
                   help='Maximum 8-paragraph pages per paper; default 3, maximum 8')
    p.add_argument('--supplements',action='store_true',help='Try actual SI archive and first file page')
    args=p.parse_args()
    if args.command=='selftest':return selftest()
    assert args.experiment and args.out,'EXPERIMENT_AND_OUT_REQUIRED'
    assert 1<=args.max_pages<=8,'MAX_PAGES_OUT_OF_RANGE'
    exp=args.experiment.expanduser().resolve(strict=True)
    dest=args.out.expanduser()
    assert not dest.exists(),'REFUSE_OVERWRITE_EXISTING_PROBE'
    mods, before,work_status = verify_population(exp)
    from e2core.research_literature import research_literature
    results=[probe_one(p,args.max_pages,args.supplements,research_literature) for p in PAPERS]
    _,after,_=verify_population(exp)
    assert before==after,'JOURNAL_CHANGED_DURING_PROBE'
    report={'status':'G14_NATIVE_PRIMARY_LITERATURE_FREE_ACCESS_PROBE',
        'generation':14,'work_id':'W_P0_primary_sers_precedent_retrieval_002',
        'work_status_at_probe':work_status,'journal_head_before_and_after':before,
        'probe_not_imported_into_journal':True,
        'model_calls_sent':0,'external_HTTP_access_attempted':True,
        'scientific_certification':False,
        'note':'A retrieved fulltext/SI is access evidence, not automatically evidence for an asserted mechanism.',
        'papers':results}
    dest.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True,default=str)+'\n'
    with dest.open('x',encoding='utf-8') as f:f.write(payload)
    print(json.dumps({'status':report['status'],'out':str(dest),
        'file_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
        'journal_unchanged':True,'provider_requests_sent':0,
        'work_status':work_status,'source_probes':[
            {'pmcid':p['paper']['pmcid'],'fulltext_paragraphs_retrieved':p['fulltext_paragraphs_retrieved'],
             'figure_captions_retrieved':p['figure_captions_retrieved'],
             'supplement_text_retrieved':p['supplement_text_retrieved'],
             'first_error':p['errors'][0] if p['errors'] else None} for p in results
        ]},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
