#!/usr/bin/env python3
"""Offline tests: actual PDF text extraction, title/DOI matching, error handling,
provenance, verified OpenAlex OA candidates, and overlay restore semantics.
"""
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from doi_open_pdf import read_open_pdf, _urlcheck, RetrievalLimit, _extract

DOI='10.1021/jp034632u'
TITLE='Single Molecule Raman Spectroscopy at the Junctions of Large Ag Nanocrystals'
PDF_URL='https://www.columbia.edu/cu/chemistry/groups/brus/pdf2/jp034632u.pdf'


def make_pdf(title=TITLE):
    name = 'test_article.pdf' if title == TITLE else 'unrelated_article.pdf'
    return Path(__file__).with_name(name).read_bytes()


def transport(url,is_metadata=False,*,pdf=None,oa_loc=True):
    if is_metadata:
        return json.dumps({'doi':'https://doi.org/'+DOI,'display_name':TITLE,
            'best_oa_location':{'is_oa':True,'pdf_url':PDF_URL} if oa_loc else None,
            'locations':[]}).encode()
    return pdf if pdf is not None else make_pdf()


class TestBridge(unittest.TestCase):
    def test_actual_pdf_page_extraction(self):
        raw=make_pdf()
        data=_extract(raw,1)
        self.assertEqual(data['page_count'],2)
        self.assertIn(DOI,data['first_text'])
        self.assertIn(TITLE[:26],data['page_text'])
    def test_success_and_evidence_details(self):
        res=read_open_pdf({'doi':DOI,'page':1},transport)
        self.assertEqual(res['status'],'DELIVERED')
        self.assertEqual(res['evidence_class'],'OA_PDF_TEXT')
        self.assertEqual(res['source_url'],PDF_URL)
        self.assertEqual(res['page_count'],2)
        self.assertEqual(len(res['source_sha256']),64)
        self.assertTrue(res['doi_pdf_identity_check']['doi_printed_in_extracted_text'])
        self.assertTrue(res['document_license_not_independently_verified'])
        self.assertFalse(res['scientific_certification'])
    def test_disallow_arbitrary_url_argument(self):
        res=read_open_pdf({'doi':DOI,'url':'https://localhost/a.pdf'},transport)
        self.assertEqual(res['status'],'REJECTED')
    def test_hosts_restricted(self):
        for url in ('http://www.columbia.edu/a.pdf',
                    'https://127.0.0.1/private.pdf',
                    'https://evil.example.org/a.pdf',
                    'https://user:pass@www.columbia.edu/a.pdf',
                    'https://www.columbia.edu:8443/a.pdf'):
            with self.assertRaises(RetrievalLimit):_urlcheck(url)
    def test_wrong_pdf_fails_without_false_evidence(self):
        wrong=make_pdf('Unrelated unrelated unrelated unrelated paper about magnetic resonance')
        def fetch(url,is_metadata=False):return transport(url,is_metadata,pdf=wrong)
        x=read_open_pdf({'doi':DOI,'page':1},fetch)
        self.assertEqual(x['status'],'EVIDENCE_UNAVAILABLE')
        self.assertFalse(x['empirical_evidence_retrieved'])
    def test_html_disguised_pdf_rejected(self):
        def fetch(url,is_metadata=False):return transport(url,is_metadata,pdf=b'<html>paywall</html>')
        x=read_open_pdf({'doi':DOI,'page':1},fetch)
        self.assertEqual(x['status'],'EVIDENCE_UNAVAILABLE')
        self.assertIn('RESPONSE_NOT_PDF_MAGIC',str(x['retrieval_attempts']))
    def test_metadata_doi_identity(self):
        def bad(url,is_metadata=False):
            if is_metadata:return json.dumps({'doi':'https://doi.org/10.1111/wrong','display_name':TITLE}).encode()
            return make_pdf()
        x=read_open_pdf({'doi':DOI,'page':1},bad)
        self.assertEqual(x['status'],'REJECTED')
    def test_no_model_url_and_page_not_int(self):
        for v in (True,0,201,'1'):
            x=read_open_pdf({'doi':DOI,'page':v},transport)
            self.assertEqual(x['status'],'REJECTED')
    def test_tool_extension_is_scoped(self):
        fake=types.ModuleType('e2core.engine')
        fake.WORKER_PROMPT='Base scientific prompt'
        class Engine:
            def _tool(self,req,context):return {'status':'ORIGINAL_TOOL'}
        fake.Engine=Engine
        with patch.dict(sys.modules,{'e2core':types.ModuleType('e2core'),'e2core.engine':fake}):
            import evolution_pdf
            original=fake.Engine._tool
            with evolution_pdf.activate():
                self.assertIn('read_open_pdf',fake.WORKER_PROMPT)
                self.assertEqual(fake.Engine()._tool({'kind':'primary_catalog'},{}),{'status':'ORIGINAL_TOOL'})
                with patch.object(evolution_pdf.doi_open_pdf,'read_open_pdf',return_value={'status':'DELIVERED'}):
                    self.assertEqual(fake.Engine()._tool({'kind':'literature_research','arguments':{'action':'read_open_pdf','doi':DOI}},{}),{'status':'DELIVERED'})
            self.assertIs(fake.Engine._tool,original)
            self.assertEqual(fake.WORKER_PROMPT,'Base scientific prompt')


if __name__=='__main__':unittest.main(verbosity=2)
