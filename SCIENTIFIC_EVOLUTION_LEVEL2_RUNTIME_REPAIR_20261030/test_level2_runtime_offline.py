"""Realistic long-ID/scaled-catalog regression without paid calls or Journal mutations."""
from __future__ import annotations
import unittest,copy
import memory_bridge as m


def problems(n=130):
    p=[{'id':'P0','parents':[],'question':'Original SERS autonomous physics question.'}]
    for i in range(1,n):
        ident=f'P_CARRY_{i:05d}_{(i*8937491):020x}_REDOX_ORIENTATION_INTERVENTION'
        parent='P0' if i<=3 else p[(i//3)]['id']
        p.append({'id':ident,'parents':[parent],
                  'question':('The mechanistic hypothesis to distinguish specific molecular and redox kinetics ')*4})
    return p

class EndToEndBudgetTests(unittest.TestCase):
    def test_minimum_legacy_encoding_fails_but_paging_succeeds(self):
        ps=problems(130)
        with self.assertRaisesRegex(RuntimeError,'PROBLEM_IDENTITIES_EXCEED'):
            m.bound_problems(ps,budget=10000)
        rows,meta=m.page_problem_context(ps,active_ids=(ps[-1]['id'],),budget=10000)
        ids={x['id'] for x in rows}
        self.assertIn('P0',ids)
        self.assertIn(ps[-1]['id'],ids)
        self.assertEqual(meta['total_problem_count'],len(ps))
        self.assertEqual(meta['full_problem_ledger_sha256'],m._digest(ps))
        self.assertTrue(meta['hidden_problems_are_not_rejected'])
        self.assertLessEqual(m.jsize(rows)+m.jsize(meta)+40,10000)
        self.assertEqual(meta['all_problem_ids_in_this_view'], 'all_problem_ids_newline_delimited' in meta)
        if meta['all_problem_ids_in_this_view']:
            exact_ids=meta['all_problem_ids_newline_delimited'].split('\n')
            self.assertEqual(len(set(exact_ids)),len(ps))
            parent_rows=meta['parent_indices_semicolon_delimited'].split(';')
            self.assertEqual(len(parent_rows),len(ps))
            for problem,encoding in zip(ps,parent_rows):
                parents=[] if not encoding else [exact_ids[int(x)] for x in encoding.split(',')]
                self.assertEqual(problem['parents'],parents)
        else:
            self.assertGreater(meta['not_visible_problem_count'],0)
        # Parent closure is not silently truncated.
        for r in rows:
            self.assertTrue(all(p in ids for p in r['parents']))

    def test_many_thousands_of_problem_ids_disclose_limited_index(self):
        ps=problems(1700)
        rows,meta=m.page_problem_context(ps,active_ids=(ps[2]['id'],),budget=7500)
        self.assertLessEqual(m.jsize(rows)+m.jsize(meta)+40,7500)
        self.assertFalse(meta['all_problem_ids_in_this_view'])
        self.assertGreater(meta['not_visible_problem_count'],1000)
        self.assertEqual(meta['full_problem_ledger_sha256'],m._digest(ps))

    def test_work_claims_and_p0_preserved_under_extra_budget_pressure(self):
        ps=problems()
        claims=[{'asset_id':'A_'+str(i),'relation':'CONDITIONAL','evidence_ids':['SRC_'+str(i)]}
                for i in range(15)]
        impacts=[{'asset_id':'A_'+str(i),'relation_to_p0':'OPEN','evidence_ids':['SRC_'+str(i)]}
                 for i in range(15)]
        active={'work_id':'W_ACTIVE','status':'ACTIVE','mode':'INFORMED',
                'problem_id':ps[-1]['id'],'question':'A real falsifiable redox experiment'}
        payload={'program':{'problem':'P0 SERS physics.'},'problems':ps,
                 'v3_science_work_options':{'active_scientific_work':[active]},
                 'assets':[{'id':'A_'+str(i),'origin':'LIVE_WORK','kind':'HYPOTHESIS',
                            'claim':'A physical claim '*20,'parent_ids':['A_PARENT']}
                            for i in range(150)],
                 'claim_prior_art_assessment':{'claim_assessments':claims},
                 'problem_level_impact':{'claim_to_problem':impacts},
                 'independent_peer_syn_portfolio':[{'peer':'A','archive':'x'*54000}],
                 'scientific_portfolio_frontier':{'text':'y'*55000},
                 'previous_population_scientific_status':{'text':'z'*25000},
                 'working_problem_state_before_decision':{'narrative':'q'*25000},
                 'objective_assessments':[{'rationale':'z'*20000}]}
        original=copy.deepcopy(payload)
        out=m.bound_advisor_payload(payload,'CTRL_D00015')
        self.assertEqual(payload,original)
        self.assertLessEqual(m.jsize(out),86000)
        self.assertEqual(out['program'],payload['program'])
        self.assertEqual(out['v3_science_work_options']['active_scientific_work'],[active])
        self.assertEqual(out['science_memory_request_receipt']['original_payload_sha256'],m._digest(payload))
        self.assertEqual([r['asset_id'] for r in out['claim_prior_art_assessment']['claim_assessments']],
                         [r['asset_id'] for r in claims])
        self.assertEqual([r['asset_id'] for r in out['problem_level_impact']['claim_to_problem']],
                         [r['asset_id'] for r in impacts])

if __name__=='__main__':unittest.main(verbosity=2)
