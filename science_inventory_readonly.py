#!/usr/bin/env python3
"""Read-only science inventory for ScientificEvolution V4 Journal (or exported snapshot).

No paid calls, no source/policy changes, and no Journal writes. This is a
metadata and model-authored claims inventory, never a physics/novelty certificate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile


def jdump(x):
    return json.dumps(x, ensure_ascii=False, indent=2, default=str)


def selected_asset(a):
    keys = ('id','kind','problem_id','work_id','status','claim','assumptions',
            'scope','predictions','limitations','parent_ids','source_ids',
            'delta_from_parents','certification','catalog_sha256','origin_step',
            'original_root','original_asset_id')
    return {k:a[k] for k in keys if k in a}


def selected_source(s):
    # Deliberately never exports a blob (fulltext / raw source or credentials).
    keys = ('id','kind','title','doi','url','source_url','access_level',
            'locator','published','publication','year')
    return {k:s[k] for k in keys if k in s}


def selected_work(w):
    keys=('id','mode','problem_id','question','research_rationale','source_ids',
          'asset_input_ids','status','last_action','outcome')
    return {k:w[k] for k in keys if k in w}


def export(s, original_problem, working, verification, events=None):
    assets={aid:selected_asset({**a,'id':aid}) for aid,a in s.assets.items()}
    source={sid:selected_source({**src,'id':sid}) for sid,src in s.sources.items()}
    work={wid:selected_work({**w,'id':wid}) for wid,w in s.work.items()}
    decisions=[{k:c[k] for k in ('id','rationale') if k in c}
               for c in s.controller_decisions[-8:]]
    result={
      'notice':'MODEL AUTHORED CLAIMS, NOT VERIFIED SCIENCE. NO PROVIDER RAW OR SOURCE TEXT EXPORTED.',
      'verified_journal':verification,
      'original_problem':original_problem,
      'counts':{'assets':len(assets),'sources':len(source),'work':len(work),
                'evolution':len(s.evolution),'controller_decisions':len(s.controller_decisions),
                'model_calls':len(s.model_calls),
                'model_call_states':{k:sum(v.get('state')==k for v in s.model_calls.values()) for k in ('SAVED','UNCERTAIN','OTHER')}},
      'works':work, 'assets':assets, 'sources_metadata_only':source,
      'evolution':[{'id':e.get('id'),'operation':e.get('operation'),
                    'asset_ids':e.get('asset_ids'), 'work_id':e.get('work_id')}
                   for e in s.evolution],
      'recent_controller_decisions':decisions,
      'last_program_review':s.program_reviews[-1] if s.program_reviews else None,
      'working_problem_model_assessment':{
          'provenance':working.get('provenance'),
          'model_assessment_only':working.get('model_assessment_only'),
          'original_problem_immutable':working.get('original_problem_immutable'),
          'latest_working_p0':working.get('latest_working_p0'),
          'original_selected_candidates':working.get('original_selected_candidates'),
          'last_claim_relation_changes':(working.get('claim_relation_changes') or [])[-30:]
      }
    }
    if events:
        result['journal_tail']=[{'seq':e.get('seq'),'kind':e.get('kind'),
                                  'payload_id':e.get('payload',{}).get('id')}
                                 for e in events[-40:]]
        result['journal_last_event_sha256']=hashlib.sha256(
            json.dumps(events[-1],ensure_ascii=False,sort_keys=True,
                       separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return result


def from_root(root):
    from e2core.core import EvolutionJournal
    import scientific_problem_evolution as spe
    j=EvolutionJournal(root)
    s=j.verify()  # fails if Journal chain or event contract is invalid
    ws=spe.working_problem_state(j)
    return export(s,(s.program or {}).get('problem'),ws,True,j._events())


def from_snapshot(path):
    d=json.loads(path.read_text(encoding='utf-8'))
    if not all(x in d for x in ('assets','sources','work','evolution','controller_decisions')):
        raise ValueError('NOT_AN_EXPORTED_SCIENCE_SNAPSHOT')
    ns=SimpleNamespace(**{k:d.get(k,{} if k in ('model_calls',) else []) for k in []})
    for k in ('assets','sources','work','evolution','controller_decisions','model_calls','program_reviews'):
        setattr(ns,k,d.get(k, [] if k in ('evolution','controller_decisions','program_reviews') else {}))
    return export(ns,d.get('program_goal'),{},'SNAPSHOT_CONTENT_ONLY__NOT_LIVE_JOURNAL_VERIFICATION')


def main():
    ap=argparse.ArgumentParser()
    src=ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--root',type=Path,help='Existing local V4 journal ROOT')
    src.add_argument('--snapshot',type=Path,help='Offline science.json snapshot for smoke test')
    ap.add_argument('--out',type=Path,required=True,help='New ZIP file in user-controlled location')
    args=ap.parse_args()
    result=from_root(args.root.expanduser()) if args.root else from_snapshot(args.snapshot)
    out=args.out.expanduser().absolute()
    if out.exists():raise FileExistsError('OUTPUT_EXISTS_REFUSING_TO_OVERWRITE:'+str(out))
    out.parent.mkdir(parents=True,exist_ok=True)
    counts=result['counts']; ranked=[a for a in result['assets'].values()
                          if a.get('kind') in ('HYPOTHESIS','PREDICTION','CALCULATION','COUNTEREXAMPLE')]
    md=['# ScientificEvolution — read-only science inventory',
        '',f'**Provenance verification:** {result["verified_journal"]}',
        '',f'**Original P0:** {result["original_problem"]}',
        '',f'**Counts:** {counts}',
        '', '## Recent controller decisions']
    for x in result['recent_controller_decisions']:
        md += [f'- {x.get("id")}: {str(x.get("rationale",""))[:950]}']
    md += ['', '## Candidate hypothesis / computation / counterexample IDs (inspect JSON for full claims)']
    for a in ranked:
        md += [f'- `{a.get("id")}` | {a.get("kind")} | {str(a.get("claim",""))[:240]}']
    md += ['', 'All science claims are model-authored, not independently validated.',
           'This export intentionally excludes raw source text, provider responses, tokens, keys and billing records.']
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('science_inventory.json',jdump(result))
        z.writestr('science_inventory_summary.md','\n'.join(md)+'\n')
    print(jdump({'created':str(out),'counts':counts,'verified_journal':result['verified_journal']}))

if __name__=='__main__':main()
