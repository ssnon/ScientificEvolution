"""Exercise actual base-context entry and paging with long problem IDs, no provider or Journal mutation."""
import copy
import unittest
from types import SimpleNamespace
import memory_bridge as m
from test_level2_runtime_offline import problems

class RealEntrypointTests(unittest.TestCase):
    def fixture(self,n=130):
        ps=problems(n)
        active={'id':'W_ACTIVE','problem_id':ps[-1]['id'],'status':'ACTIVE','mode':'INFORMED'}
        state=SimpleNamespace(
            work={'W_ACTIVE':active}, assets={},tool_results={},
            problems={x['id']:x for x in ps},sources={})
        base={'program':{'problem':'P0 is untouched.'},'problems':ps,
              'assets':[], 'v3_science_work_options':{'active_scientific_work':[active]}}
        return ps,base,state

    def test_bound_base_falls_back_before_nvt_or_pmi(self):
        ps,base,state=self.fixture()
        # This is the exact entrypoint omitted by earlier tests.
        with self.assertRaisesRegex(RuntimeError,'PROBLEM_IDENTITIES_EXCEED'):
            m.bound_problems(ps,budget=22000)
        copy_base=copy.deepcopy(base)
        view=m.bound_base(base,state,'readonly-journal')
        self.assertEqual(base,copy_base)
        self.assertEqual(view['program'],base['program'])
        self.assertIn('problem_attention_catalog',view)
        self.assertEqual(view['problem_attention_catalog']['full_problem_ledger_sha256'],m._digest(ps))
        self.assertEqual(view['problem_attention_catalog']['total_problem_count'],len(ps))
        self.assertIn(ps[-1]['id'],[x['id'] for x in view['problems']])
        self.assertEqual(view['problem_attention_info']['all_ids_kept_in_original_problems_list'],
                         len(view['problems'])==len(ps))
        self.assertLessEqual(m.jsize(view['problems'])+m.jsize(view['problem_attention_catalog'])+40,22000)

    def test_repage_does_not_reset_historical_universe(self):
        ps,base,state=self.fixture()
        view=m.bound_base(base,state,'readonly-journal')
        cat=view['problem_attention_catalog']
        ids=[x['id'] for x in view['problems']]
        for budget in (17000,13000,10000):
            rows,cat=m.rebudget_existing_problem_page(view['problems'],cat,budget)
            self.assertEqual([x['id'] for x in rows],ids)
            self.assertEqual(cat['full_problem_ledger_sha256'],m._digest(ps))
            self.assertEqual(cat['total_problem_count'],len(ps))
            self.assertEqual(cat['not_visible_problem_count'],len(ps)-len(rows))
            self.assertLessEqual(m.jsize(rows)+m.jsize(cat)+40,budget)

    def test_full_pipeline_retains_hash_p0_active_work_and_full_universe(self):
        ps,base,state=self.fixture()
        view=m.bound_base(base,state,'readonly-journal')
        view.update({
            'scientific_portfolio_frontier':{'research':'History '*16000},
            'independent_peer_syn_portfolio':[{'peer':'A','science':'Independent '*12000}],
            'previous_population_scientific_status':{'details':'Old work '*7000},
            'working_problem_state_before_decision':{'details':'Interpretation '*3000},
            'prior_program_reviews':[{'rationale':'Old '+ 'review '*7000}],
        })
        original=copy.deepcopy(view)
        bounded=m.bound_advisor_payload(view,'OPP_D00011')
        self.assertEqual(view,original)
        self.assertLessEqual(m.jsize(bounded),m.BUDGETS['all_controller'])
        self.assertEqual(bounded['program'],base['program'])
        self.assertEqual(bounded['v3_science_work_options']['active_scientific_work'],
                         base['v3_science_work_options']['active_scientific_work'])
        self.assertEqual(bounded['science_memory_request_receipt']['original_payload_sha256'],m._digest(view))
        cat=bounded['problem_attention_catalog']
        self.assertEqual(cat['full_problem_ledger_sha256'],m._digest(ps))
        self.assertEqual(cat['total_problem_count'],len(ps))

if __name__=='__main__':unittest.main(verbosity=2)
