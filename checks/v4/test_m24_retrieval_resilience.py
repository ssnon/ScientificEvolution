"""M24 no-network regression: real Native search function + fake providers."""
import json
import os
import unittest
import urllib.error
from unittest import mock
from e2core import research_literature as module


class TestM24RetrievalResilience(unittest.TestCase):
    query='single molecule SERS blinking spectral diffusion'

    def _openalex(self, url):
        return json.dumps({'results':[{ 'id':'https://openalex.org/W123456789',
            'display_name':'Test publication (not evidence)',
            'publication_year':2024,'doi':'https://doi.org/10.1234/example',
            'open_access':{'is_oa':True}}]}).encode()

    def _epmc(self, url):
        return json.dumps({'resultList':{'result':[{ 'id':'1234','source':'MED',
            'pmcid':'PMC1234','title':'Test publication (not evidence)',
            'pubYear':'2024','doi':'10.1234/example','isOpenAccess':'Y','inEPMC':'Y'}]}}).encode()

    def _status(self,url,code):
        raise urllib.error.HTTPError(url,code,'test provider response',hdrs={},fp=None)

    def test_openalex_429_falls_back_to_europepmc_without_extra_model_call(self):
        calls=[]
        def transport(url):
            calls.append(url)
            if 'api.openalex.org' in url:self._status(url,429)
            return self._epmc(url)
        out=module.research_literature({'action':'search','provider':'openalex',
            'query':self.query,'page':1},transport=transport,sleeper=lambda _:None)
        self.assertEqual(out['status'],'DELIVERED')
        self.assertEqual(out['provider'],'europepmc')
        self.assertEqual(out['requested_provider'],'openalex')
        self.assertEqual(out['fallback_reason'],'OPENALEX_HTTP_429')
        self.assertEqual(out['evidence_class'],'BIBLIOGRAPHIC_METADATA')
        self.assertFalse(out['records'][0]['claims_about_experiments_verified'])
        self.assertEqual(len(calls),2)
        self.assertEqual([x['http_status'] for x in out['retrieval_attempts']],[429,200])

    def test_europepmc_503_still_falls_back_to_openalex(self):
        def transport(url):
            if 'europepmc' in url:self._status(url,503)
            return self._openalex(url)
        out=module.research_literature({'action':'search','provider':'europepmc',
            'query':self.query,'page':1},transport=transport,sleeper=lambda _:None)
        self.assertEqual(out['status'],'DELIVERED')
        self.assertEqual(out['requested_provider'],'europepmc')
        self.assertEqual(out['fallback_provider'],'openalex')
        self.assertEqual(out['fallback_reason'],'EUROPEPMC_HTTP_503')
        self.assertEqual(out['evidence_class'],'BIBLIOGRAPHIC_METADATA')
        self.assertEqual([x['http_status'] for x in out['retrieval_attempts']],[503,503,200])

    def test_both_providers_unavailable_never_claims_scientific_absence(self):
        def transport(url):
            self._status(url,429 if 'openalex' in url else 503)
        out=module.research_literature({'action':'search','provider':'openalex',
            'query':self.query,'page':1},transport=transport,sleeper=lambda _:None)
        self.assertEqual(out['status'],'EVIDENCE_UNAVAILABLE')
        self.assertEqual(out['evidence_class'],'NO_EVIDENCE_RETRIEVED')
        self.assertFalse(out['empirical_evidence_retrieved'])
        self.assertTrue(out['availability_not_evidence_of_scientific_absence'])
        self.assertEqual([x['http_status'] for x in out['retrieval_attempts']],[429,503,503])

    def test_non_transient_bad_request_does_not_fallback(self):
        called=[]
        def transport(url):
            called.append(url);self._status(url,400)
        out=module.research_literature({'action':'search','provider':'openalex',
            'query':self.query,'page':1},transport=transport,sleeper=lambda _:None)
        self.assertEqual(out['status'],'REJECTED')
        self.assertEqual(len(called),1)

    def test_bearer_key_header_not_url_or_model_trace(self):
        captured=[]
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,n):return b'{}'
        class Opener:
            def open(self,req,timeout):
                captured.append((req.full_url,req.get_header('Authorization')))
                return Response()
        with mock.patch.dict(os.environ,{'OPENALEX_API_KEY':'test-secret-123'}):
            with mock.patch.object(module.urllib.request,'build_opener',return_value=Opener()):
                self.assertEqual(module._network('https://api.openalex.org/works?search=x'),b'{}')
        self.assertEqual(captured[0][1],'Bearer test-secret-123')
        self.assertNotIn('test-secret-123',captured[0][0])

    def test_europepmc_never_receives_openalex_key(self):
        captured=[]
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,n):return b'{}'
        class Opener:
            def open(self,req,timeout):
                captured.append((req.full_url,req.get_header('Authorization')))
                return Response()
        with mock.patch.dict(os.environ,{'OPENALEX_API_KEY':'test-secret-123'}):
            with mock.patch.object(module.urllib.request,'build_opener',return_value=Opener()):
                module._network('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x')
        self.assertIsNone(captured[0][1])


if __name__=='__main__':unittest.main()
