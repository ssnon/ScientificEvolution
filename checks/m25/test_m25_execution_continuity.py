"""No-paid tests for two M24-grounded interface faults and factual Work feedback."""
from __future__ import annotations
import json
import unittest
from types import SimpleNamespace

from e2core.research_literature import research_literature
from e2core.research_context import observed_work_outcomes

XML = (b'<?xml version="1.0" encoding="UTF-8"?>'
       b'<article><front><article-meta><title-group><article-title>Test primary report</article-title>'
       b'</title-group></article-meta></front><body><sec><title>Methods</title>'
       b'<p id="p1">Measured simultaneous Raman state and sample occupancy '
       b'with independently defined time resolution and field controls.</p>'
       b'</sec></body></article>')

class MockJournal:
    def __init__(self):
        self.items={
          'Q1': {'kind':'literature_research','arguments':{'action':'search','query':'SERS'}},
          'R1': {'status':'DELIVERED','evidence_class':'BIBLIOGRAPHIC_METADATA','linked_source_id':'S_META'},
          'Q2': {'kind':'literature_research','arguments':{'action':'read_fulltext','pmcid':'PMC12648421'}},
          'R2': {'status':'DELIVERED','evidence_class':'OA_FULLTEXT_TEXT','paragraphs':[{'text':'Measured'}], 'linked_source_id':'S_TEXT'},
          'Q3': {'kind':'literature_research','arguments':{'action':'read_fulltext','pmcid':'12648421'}},
          'R3': {'status':'REJECTED','error_code':'INVALID_PMCID'},
        }
        self.state=SimpleNamespace(
            tool_results={
              'TOOL_W_A_01':{'work_id':'W_A','request_blob':'Q1','result_blob':'R1'},
              'TOOL_W_A_02':{'work_id':'W_A','request_blob':'Q3','result_blob':'R3'},
              'TOOL_W_B_01':{'work_id':'W_B','request_blob':'Q2','result_blob':'R2'},
            },
            assets={
              'A_A':{'id':'A_A','kind':'HYPOTHESIS','source_ids':[]},
              'A_B':{'id':'A_B','kind':'LITERATURE_CLAIM','source_ids':['S_TEXT']},
            },
            work={
              'W_A':{'question':'Inspect exact primary body; theory may be written regardless','status':'DONE','outcome':'RETURN','published':['A_A']},
              'W_B':{'question':'Find referenced methods','status':'ACTIVE','outcome':None,'published':['A_B']},
              'W_C':{'question':'Explore mathematical null','status':'DONE','outcome':'RETURN','published':[]},
            })
    def verify(self):return self.state
    def raw(self,key):return json.dumps(self.items[key]).encode()

class TestM25(unittest.TestCase):
    def test_numeric_pmcid_and_json_decimal_pagination_repaired_without_network(self):
        requests=[]
        def transport(url):
            requests.append(url)
            self.assertEqual(url,'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12648421/fullTextXML')
            return XML
        authored={'action':'read_fulltext','pmcid':'12648421','offset':'0','limit':'5'}
        original=authored.copy()
        x=research_literature(authored,transport=transport)
        self.assertEqual(x['status'],'DELIVERED',x)
        self.assertEqual(x['evidence_class'],'OA_FULLTEXT_TEXT')
        self.assertEqual(x['pmcid'],'PMC12648421')
        self.assertEqual(len(x['paragraphs']),1)
        self.assertEqual(authored,original,'Do not rewrite model-authored tool request')
        self.assertEqual(len(requests),1)

    def test_prefixed_pmcid_unchanged(self):
        x=research_literature({'action':'read_fulltext','pmcid':'PMC12648421','offset':0,'limit':2},transport=lambda url:XML)
        self.assertEqual(x['status'],'DELIVERED',x)
        self.assertEqual(x['pmcid'],'PMC12648421')

    def test_integer_encoded_pmcid_canonicalized_not_guessed(self):
        x=research_literature({'action':'read_fulltext','pmcid':12648421,'offset':0,'limit':5},transport=lambda url:XML)
        self.assertEqual(x['status'],'DELIVERED',x)
        self.assertEqual(x['pmcid'],'PMC12648421')

    def test_invalid_identifier_rejected_without_network(self):
        n=[]
        for bad in ('PMC12X','https://foo/PMC123','',True):
            x=research_literature({'action':'read_fulltext','pmcid':bad},transport=lambda url:n.append(url) or XML)
            self.assertEqual(x['status'],'REJECTED',x)
            self.assertEqual(x['error_code'],'INVALID_PMCID',x)
        self.assertEqual(n,[])

    def test_invalid_pagination_is_not_silently_corrected(self):
        requests=[]
        for v in ('-1','5.0','bad',True):
            x=research_literature({'action':'read_fulltext','pmcid':'PMC12648421','offset':v},transport=lambda u:requests.append(u) or XML)
            self.assertEqual(x['status'],'REJECTED',x)
        self.assertEqual(requests,[])

    def test_work_output_and_original_question_are_separate(self):
        j=MockJournal()
        out={x['work_id']:x for x in observed_work_outcomes(j)}
        self.assertEqual(out['W_A']['actual_evidence_classes'],{'BIBLIOGRAPHIC_METADATA':1,'UNCLASSIFIED':1})
        self.assertEqual(out['W_A']['model_authored_asset_count'],1)
        self.assertEqual(out['W_A']['direct_text_tool_ids'],[])
        self.assertEqual(out['W_A']['current_work_status'],'DONE')
        self.assertEqual(out['W_A']['scientific_question_resolved'],'NOT_DETERMINED_BY_OPERATIONAL_LEDGER')
        self.assertEqual(out['W_B']['direct_text_tool_ids'],['TOOL_W_B_01'])
        self.assertEqual(out['W_C']['actual_tool_count'],0)
        # No inference of absence of real-world evidence or of scientific failure.
        self.assertEqual(out['W_C']['scientific_question_resolved'],'NOT_DETERMINED_BY_OPERATIONAL_LEDGER')

    def test_worker_private_scope(self):
        j=MockJournal()
        x=observed_work_outcomes(j,only_work_id='W_A')
        self.assertEqual(len(x),1)
        self.assertEqual(x[0]['work_id'],'W_A')
        self.assertNotIn('TOOL_W_B_01',str(x))
        self.assertNotIn('A_B',str(x))

if __name__=='__main__':unittest.main()
