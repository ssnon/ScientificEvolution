"""M21.1 fake-network regression; never makes external HTTP/model calls."""
from __future__ import annotations
import json
import unittest
from e2core.oa_pdf import read_from_openalex_record, OAPDFError
from e2core.research_literature import research_literature
from test_m21_oa_pdf import make_pdf, TITLE, DOI

AUTHOR_URL='https://authors.example.edu/oa/experiment_main.pdf'
OLD_URL='https://archive.example.edu/paper.pdf'
SEM_URL='https://repository.example.edu/preprint.pdf'
META={'doi':DOI,'title':TITLE,'best_oa_pdf_url':OLD_URL,'other_oa_locations':[]}

def oa_work():
    return {'id':'https://openalex.org/W2219488342',
        'doi':'https://doi.org/'+DOI, 'display_name':TITLE,
        'open_access':{'is_oa':True},'best_oa_location':{'pdf_url':OLD_URL},
        'locations':[]}

def sem_work(doi=DOI,title=TITLE, url=SEM_URL):
    return {'title':title, 'externalIds':{'DOI':doi},'openAccessPdf':{'url':url}}

class OAExpandedDiscoveryTests(unittest.TestCase):
    def test_author_site_candidate_url_is_doi_title_checked_and_traceable(self):
        called=[]
        def fetch(url):
            called.append(url)
            if url==AUTHOR_URL:return make_pdf()
            raise AssertionError('Must not try unusable legacy URL after successful lead')
        got=read_from_openalex_record({'doi':DOI,'page':1,'candidate_url':AUTHOR_URL},META,fetch)
        self.assertEqual(got['status'],'DELIVERED',got)
        self.assertEqual(called,[AUTHOR_URL])
        self.assertEqual(got['candidate_provenance'],'WORKER_SUGGESTED_UNVERIFIED_URL_PDF_TITLE_CHECKED')
        self.assertEqual(got['source_url'],AUTHOR_URL)
        self.assertEqual(got['evidence_class'],'OA_PDF_TEXT')

    def test_arbitrary_candidate_still_rejected_before_network(self):
        for candidate in ['http://authors.example.edu/a.pdf','https://127.0.0.1/a.pdf',
                          'https://localhost/a.pdf','https://authors.example.edu:1234/a.pdf']:
            with self.subTest(candidate=candidate):
                got=read_from_openalex_record({'doi':DOI,'page':1,'candidate_url':candidate},
                    {'doi':DOI,'title':TITLE,'best_oa_pdf_url':'','other_oa_locations':[]},
                    lambda url: (_ for _ in ()).throw(AssertionError('BAD_NETWORK')))
                self.assertEqual(got['status'],'EVIDENCE_UNAVAILABLE')
                self.assertTrue(got['candidate_attempts'])

    def test_suggested_url_wrong_document_never_delivered(self):
        got=read_from_openalex_record({'doi':DOI,'page':1,'candidate_url':AUTHOR_URL},
            {'doi':DOI,'title':TITLE,'best_oa_pdf_url':''},
            lambda url:make_pdf('Unrelated paper on ancient geology and volcanology'))
        self.assertNotEqual(got['status'],'DELIVERED')

    def test_semantic_scholar_fallback_is_doi_matched(self):
        events=[]
        def transport(url):
            events.append(url)
            if 'api.openalex.org/works/' in url:return json.dumps(oa_work()).encode()
            if url==OLD_URL:raise OAPDFError('OFFLINE_ARCHIVE_UNAVAILABLE')
            if 'api.semanticscholar.org/graph/v1/paper/DOI:' in url:
                return json.dumps(sem_work()).encode()
            if url==SEM_URL:return make_pdf()
            raise AssertionError('Unexpected URL: '+url)
        got=research_literature({'action':'read_oa_pdf','doi':DOI,'page':1},transport=transport)
        self.assertEqual(got['status'],'DELIVERED',got)
        self.assertEqual(got['source_url'],SEM_URL)
        self.assertEqual(got['candidate_provenance'],'DOI_MATCHED_SEMANTIC_SCHOLAR_METADATA')
        self.assertEqual(len(got['retrieval_attempts']),3)
        self.assertEqual(len(events),4)

    def test_semantic_wrong_doi_never_triggers_second_pdf(self):
        events=[]
        def transport(url):
            events.append(url)
            if 'api.openalex.org/works/' in url:return json.dumps(oa_work()).encode()
            if url==OLD_URL:raise OAPDFError('UNAVAILABLE')
            if 'api.semanticscholar.org/' in url:
                return json.dumps(sem_work(doi='10.1000/WRONG')).encode()
            raise AssertionError('Must not fetch Semantic PDF when DOI mismatched')
        got=research_literature({'action':'read_oa_pdf','doi':DOI,'page':1},transport=transport)
        self.assertEqual(got['status'],'EVIDENCE_UNAVAILABLE')
        self.assertEqual(len(events),3)
        self.assertIn('SEMANTIC_SCHOLAR_DOI_IDENTITY_UNVERIFIED',
            got['additional_discovery_attempts'][0]['reason'])

    def test_semantic_wrong_title_never_triggers_second_pdf(self):
        events=[]
        def transport(url):
            events.append(url)
            if 'api.openalex.org/works/' in url:return json.dumps(oa_work()).encode()
            if url==OLD_URL:raise OAPDFError('UNAVAILABLE')
            if 'api.semanticscholar.org/' in url:
                return json.dumps(sem_work(title='Ancient volcanic minerals in Mediterranean basin')).encode()
            raise AssertionError('Must not fetch Semantic PDF when title mismatched')
        got=research_literature({'action':'read_oa_pdf','doi':DOI,'page':1},transport=transport)
        self.assertEqual(got['status'],'EVIDENCE_UNAVAILABLE')
        self.assertIn('SEMANTIC_SCHOLAR_TITLE_MISMATCH',
            got['additional_discovery_attempts'][0]['reason'])

    def test_native_action_accepts_optional_author_lead(self):
        events=[]
        def transport(url):
            events.append(url)
            if 'api.openalex.org/works/' in url:return json.dumps(oa_work()).encode()
            if url==AUTHOR_URL:return make_pdf()
            raise AssertionError('Did not expect:'+url)
        result=research_literature({'action':'read_oa_pdf','doi':DOI,
            'candidate_url':AUTHOR_URL,'page':1},transport=transport)
        self.assertEqual(result['status'],'DELIVERED',result)
        self.assertEqual(len(result['retrieval_attempts']),2)
        self.assertEqual(events[-1],AUTHOR_URL)

if __name__=='__main__':unittest.main(verbosity=2)
