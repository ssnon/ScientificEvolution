import unittest
from e2core.m232_context import build_impact_context, _hash


class M232ContextTests(unittest.TestCase):
    def test_full_cited_and_catalog_provenance(self):
        evidence = [
            {'evidence_id':'SRC_A','inspection_class':'OA_FULLTEXT_TEXT', 'source_kind':'EXTERNAL_AUDIT', 'returned_content':'full paper evidence'},
            {'evidence_id':'SRC_B','inspection_class':'OA_FULLTEXT_TEXT', 'source_kind':'EXTERNAL_AUDIT', 'returned_content':'other complete text'},
        ]
        problems=[{'id':'P0','status':'OPEN','parents':[],'question':'Original P0 full'},
                  {'id':'P1','parents':['P0'],'status':'OPEN','question':'relevant issue'},
                  {'id':'P2','parents':['P0'],'status':'OPEN','question':'unrelated issue'}]
        novelty={'claim_assessments':[{'asset_id':'A1','evidence_ids':['SRC_A']}]} 
        obj = build_impact_context(program={'problem':'Original P0 full','criteria':'Level II'},
             problems=problems,novelty=novelty,evidence=evidence,prior_state={'current_claim_assessments':{}},
             prior_art_delta={},focus_problem_ids=['P1'])
        self.assertEqual(obj['evidence'][0], evidence[0])
        cat=obj['evidence'][1]
        self.assertEqual(cat['evidence_id'],'SRC_B')
        self.assertNotIn('returned_content',cat)
        self.assertEqual(cat['inspection_class'],'CATALOG_ONLY_NOT_INSPECTED_IN_THIS_CALL')
        self.assertEqual(cat['registered_inspection_class'],'OA_FULLTEXT_TEXT')
        self.assertEqual(obj['current_problems'][0],problems[0])
        self.assertEqual(obj['current_problems'][1],problems[1])
        self.assertTrue('question_preview_not_full_problem' in obj['current_problems'][2])
        self.assertTrue(obj['original_p0_unchanged'])
        self.assertEqual(evidence[1]['returned_content'], 'other complete text')
        self.assertEqual(set(obj['context_scope']['catalog_only_evidence_ids']), {'SRC_B'})

    def test_prior_citations_and_determinism(self):
        p=[{'id':'P0','parents':[],'question':'P0'}]
        ev=[{'evidence_id':'S1','inspection_class':'BIBLIOGRAPHIC_METADATA'},
            {'evidence_id':'S2','inspection_class':'OA_FULLTEXT_CAPTION','returned_content':'caption'},
            {'evidence_id':'S3','inspection_class':'OA_PDF_TEXT','returned_content':'text'}]
        kw=dict(program={'problem':'P0'},problems=p,
                novelty={'claim_assessments':[{'asset_id':'A','evidence_ids':['S1']}]}, evidence=ev,
                prior_state={'current_claim_assessments':{'A':{'evidence_ids':['S3']}}},prior_art_delta={})
        a=build_impact_context(**kw);b=build_impact_context(**kw)
        self.assertEqual(_hash(a),_hash(b))
        self.assertEqual(set(a['context_scope']['full_evidence_ids']), {'S1','S3'})
        self.assertEqual(set(a['context_scope']['catalog_only_evidence_ids']), {'S2'})

    def test_no_novelty_citations_all_index_only(self):
        a=build_impact_context(program={'problem':'p0'},problems=[{'id':'P0','parents':[],'question':'p0'}],
            novelty={'claim_assessments':[]},evidence=[{'evidence_id':'SRC_DIRECT','inspection_class':'OA_FULLTEXT_TEXT', 'returned_content':'content'}],
            prior_state={},prior_art_delta={})
        self.assertEqual(a['evidence'][0]['inspection_class'],'CATALOG_ONLY_NOT_INSPECTED_IN_THIS_CALL')
        self.assertTrue(a['context_scope']['all_evidence_ids_catalogued'])
        self.assertFalse(a['evidence'][0]['detail_present_in_this_call'])

if __name__=='__main__':unittest.main()
