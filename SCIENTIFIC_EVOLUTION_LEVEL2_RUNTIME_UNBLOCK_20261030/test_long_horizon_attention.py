"""Stress the actual bounded-input function without calling provider or Journal."""
import copy,unittest
import memory_bridge as mm

class Tests(unittest.TestCase):
    def make(self):
        ps=[{'id':'P0','parents':[],'question':'Original experimental SERS question'}]
        ps += [{'id':'P'+str(k),'parents':['P0'],
            'question':'Derived experimental mechanism with complex assumptions '*30} for k in range(1,139)]
        assets=[{'id':f'A_{i}', 'claim':'Source-bounded scientific mechanistic hypotheses '*38,
                 'origin':'LIVE_WORK','kind':'HYPOTHESIS','source_ids':[],
                 'parent_ids':['A_PARENT'], 'predictions':['some specific test '*20]}
                for i in range(430)]
        claims=[{'asset_id':f'A_{i}','relation':'CONDITIONAL','evidence_ids':['SRC_'+str(i)],
                'specific_differentiating_prediction':'More precise independent intervention '*12}
                for i in range(19)]
        impacts=[{'asset_id':c['asset_id'],'relation_to_p0':'P0_OPEN','evidence_ids':c['evidence_ids'],
             'impact_on_solution':'still conditional '*20} for c in claims]
        live=[{'work_id':'W_live','mode':'INFORMED','status':'ACTIVE',
               'question':'Current selective redox intervention', 'published_count':1, 'steps':9}]
        return {'program':{'problem':'Original experimental SERS question'},'problems':ps,
            'assets':assets,'claim_prior_art_assessment':{'claim_assessments':claims},
            'problem_level_impact':{'claim_to_problem':impacts},
            'v3_science_work_options':{'active_scientific_work':live},
            'science_memory_disclosure':{'version':mm.VERSION},
            'scientific_portfolio_frontier':{'research_text':'historical state '*2000},
            'independent_peer_syn_portfolio':[{'peer':'a','legacy_report':'literature '*6000}],
            'working_problem_state_before_decision':{'science':'X'*15000},
            'scientific_evidence_inventory':{'evidence':'Y'*10000},
            'prior_program_reviews':[{'rationale':'no decisive evidence '*3000}],
            'objective_assessments':[{'rationale':'unresolved situation '*3000}]}
    def test_adaptive_preserves_reference_ledgers(self):
        p=self.make();before=copy.deepcopy(p)
        out=mm.bound_advisor_payload(p,'OPP_D00008')
        self.assertLessEqual(mm.jsize(out),86000)
        self.assertEqual(p,before)
        self.assertEqual(p['program'],out['program'])
        self.assertEqual([i['id'] for i in p['problems']],[i['id'] for i in out['problems']])
        self.assertEqual([i['parents'] for i in p['problems']],[i['parents'] for i in out['problems']])
        for field,row_key,items in [('claim_prior_art_assessment','claim_assessments',('asset_id','relation','evidence_ids')),
                                    ('problem_level_impact','claim_to_problem',('asset_id','relation_to_p0','evidence_ids'))]:
            self.assertEqual([tuple(x.get(k) for k in items if k!='evidence_ids')+(tuple(x.get('evidence_ids',[])),)
                              for x in p[field][row_key]],
                             [tuple(x.get(k) for k in items if k!='evidence_ids')+(tuple(x.get('evidence_ids',[])),)
                              for x in out[field][row_key]])
        self.assertEqual(out['v3_science_work_options']['active_scientific_work'],
                         p['v3_science_work_options']['active_scientific_work'])
        self.assertEqual(out['science_memory_request_receipt']['original_payload_sha256'],mm._digest(p))
    def test_uncompressible_program_still_blocks(self):
        with self.assertRaisesRegex(RuntimeError,'MODEL_ATTENTION_BUDGET_UNSATISFIED'):
            mm.bound_advisor_payload({'program':{'problem':'P'*90000}},'OPP_D00008')
if __name__=='__main__':unittest.main(verbosity=2)
