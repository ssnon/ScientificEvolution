"""Fake OpenAlex + fake PDF integration: exercise the actual native action router."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
if not (REPO/'runtime'/'e2core'/'research_literature.py').exists():
    # Kit-only tests: skip integration until source is installed in worktree.
    NATIVE_PRESENT=False
else:
    NATIVE_PRESENT=True
    sys.path.insert(0,str(REPO/'runtime'))
    from e2core.research_literature import research_literature
from test_m21_oa_pdf import make_pdf,TITLE,DOI,PUBLIC_URL

@unittest.skipUnless(NATIVE_PRESENT,'Run against the dedicated patched repository to test native integration')
class NativeResearchIntegrationTest(unittest.TestCase):
    def test_resolve_pdf_read_with_exact_provenance(self):
        seen=[]
        work={'id':'https://openalex.org/W2219488342',
              'doi':'https://doi.org/'+DOI,'display_name':TITLE,'publication_year':2015,
              'open_access':{'is_oa':True},
              'best_oa_location':{'pdf_url':PUBLIC_URL,'landing_page_url':'','is_oa':True},
              'locations':[{'is_oa':True,'pdf_url':PUBLIC_URL,'landing_page_url':''}]}
        def transport(url):
            seen.append(url)
            if url.startswith('https://api.openalex.org/works/'):return json.dumps(work).encode()
            if url==PUBLIC_URL:return make_pdf()
            raise AssertionError('FAKE_TRANSPORT_UNEXPECTED_URL:'+url)
        actual=research_literature({'action':'read_oa_pdf','doi':DOI,'page':1},transport=transport)
        self.assertEqual(actual['status'],'DELIVERED',actual)
        self.assertEqual(actual['evidence_class'],'OA_PDF_TEXT')
        self.assertEqual(actual['page_count'],1)
        self.assertTrue(actual['source_sha256'])
        self.assertEqual(len(actual['retrieval_attempts']),2)
        self.assertEqual(seen[-1],PUBLIC_URL)
        self.assertFalse(actual['scientific_certification'])

if __name__=='__main__':unittest.main(verbosity=2)
