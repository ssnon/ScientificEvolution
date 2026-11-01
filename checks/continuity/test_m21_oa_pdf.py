"""Offline-only M21 OA acquisition tests; NO external provider/model/network calls."""
from __future__ import annotations
import hashlib
import json
import sys
import unittest
from pathlib import Path

# Supports running as a bundled kit, and after installing into repo/checks.
HERE=Path(__file__).resolve().parent
if (HERE/'oa_pdf.py').exists():sys.path.insert(0,str(HERE))
else:sys.path.insert(0,str(HERE.parents[1]/'runtime'/'e2core'))
import oa_pdf

TITLE='Variable Temperature Tip Enhanced Raman Spectroscopy of Single Molecule Fluctuations and Dynamics'
DOI='10.1021/acs.nanolett.5b04135'
PUBLIC_URL='https://research.example.edu/verified/author-article.pdf'

def make_pdf(title=TITLE):
    """Generate a minimal in-memory text PDF without a third-party PDF writer."""
    # ASCII string content to keep text extraction deterministic.
    data=(title+' A study of spectroscopy with controlled sample measurements').replace('(','').replace(')','')
    stream=f'BT /F1 12 Tf 50 750 Td ({data}) Tj ET'.encode('ascii')
    objects=[
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    pdf=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(pdf));pdf.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref=len(pdf);pdf.extend(f'xref\n0 {len(objects)+1}\n'.encode()+b'0000000000 65535 f \n')
    for pos in offsets[1:]:pdf.extend(f'{pos:010d} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(pdf)

class OAPDFOfflineTests(unittest.TestCase):
    def test_public_domain_policy(self):
        self.assertEqual(oa_pdf.checked_public_https_url(PUBLIC_URL)[0],'research.example.edu')
        for bad in ['http://research.example.edu/a.pdf','https://127.0.0.1/a.pdf',
                    'https://[::1]/a.pdf','https://user:password@research.example.edu/a.pdf',
                    'https://localhost/a.pdf','https://intranet.local/a.pdf',
                    'https://research.example.edu:8080/a.pdf',
                    'https://research.example.edu/a.pdf#x',
                    'https://research.example.edu/ab\\cd.pdf',
                    'https://192.168.1.5/a.pdf']:
            with self.subTest(bad=bad),self.assertRaises(oa_pdf.OAPDFError):
                oa_pdf.checked_public_https_url(bad)

    def test_dns_rejects_private_and_mixed(self):
        from unittest.mock import patch
        import socket
        fake=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.3.4.5',443))]
        with patch.object(oa_pdf.socket,'getaddrinfo',return_value=fake):
            with self.assertRaisesRegex(oa_pdf.OAPDFError,'NONPUBLIC'):
                oa_pdf._checked_dns('research.example.edu')
        mixed=fake+[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
        with patch.object(oa_pdf.socket,'getaddrinfo',return_value=mixed):
            with self.assertRaisesRegex(oa_pdf.OAPDFError,'NONPUBLIC'):
                oa_pdf._checked_dns('research.example.edu')

    def test_redirect_to_private_host_is_rejected_before_second_fetch(self):
        from unittest.mock import patch
        attempts=[]
        def fake_one(url):
            attempts.append(url)
            return {'status':302,'location':'https://127.0.0.1/admin',
                    'body':b'','content_type':'text/plain'}
        with patch.object(oa_pdf,'_one_request',side_effect=fake_one):
            with self.assertRaises(oa_pdf.OAPDFError):
                oa_pdf.public_pdf_get(PUBLIC_URL)
        self.assertEqual(attempts,[PUBLIC_URL])

    def test_redirect_chain_and_pdf_content(self):
        from unittest.mock import patch
        final='https://publisher.example.edu/oa/author_copy.pdf'
        calls=[]
        def fake_one(url):
            calls.append(url)
            if url==PUBLIC_URL:
                return {'status':302,'location':final,'body':b'','content_type':'text/html'}
            return {'status':200,'location':None,'body':make_pdf(),'content_type':'application/pdf'}
        with patch.object(oa_pdf,'_one_request',side_effect=fake_one):
            result=oa_pdf.public_pdf_get(PUBLIC_URL)
        self.assertEqual(calls,[PUBLIC_URL,final])
        self.assertEqual(result.redirect_chain[-1]['url'],final)
        self.assertTrue(result.startswith(b'%PDF-'))

    def test_pdf_page_identity_and_source(self):
        payload=make_pdf()
        record={'doi':DOI,'title':TITLE,'best_oa_pdf_url':PUBLIC_URL,'other_oa_locations':[]}
        seen=[]
        def fake(url):
            seen.append(url)
            return payload
        got=oa_pdf.read_from_openalex_record({'doi':DOI,'page':1},record,fake)
        self.assertEqual(got['status'],'DELIVERED',got)
        self.assertEqual(got['evidence_class'],'OA_PDF_TEXT')
        self.assertIn('Tip Enhanced Raman',got['page_text'])
        self.assertEqual(got['source_sha256'],hashlib.sha256(payload).hexdigest())
        self.assertEqual(got['page'],1)
        self.assertEqual(seen,[PUBLIC_URL])

    def test_bad_pdf_and_wrong_title_never_delivered(self):
        rec={'doi':DOI,'title':TITLE,'best_oa_pdf_url':PUBLIC_URL,'other_oa_locations':[]}
        for payload in [b'<html>not pdf</html>', make_pdf('Completely unrelated volcanic mineral layers in ancient rocks')]:
            got=oa_pdf.read_from_openalex_record({'doi':DOI,'page':1},rec,lambda _:payload)
            self.assertNotEqual(got['status'],'DELIVERED')
            self.assertNotIn('page_text',got)

    def test_bad_doi_and_page_without_network(self):
        rec={'doi':DOI,'title':TITLE,'best_oa_pdf_url':PUBLIC_URL}
        def nope(url):raise AssertionError('SHOULD_NOT_FETCH')
        self.assertEqual(oa_pdf.read_from_openalex_record({'doi':'10.1111/unrelated','page':1},rec,nope)['status'],'REJECTED')
        self.assertEqual(oa_pdf.read_from_openalex_record({'doi':DOI,'page':0},rec,nope)['status'],'REJECTED')

    def test_oa_metadata_no_pdf_no_claim(self):
        rec={'doi':DOI,'title':TITLE,'best_oa_pdf_url':'','other_oa_locations':[]}
        got=oa_pdf.read_from_openalex_record({'doi':DOI,'page':1},rec,lambda _:b'')
        self.assertEqual(got['status'],'EVIDENCE_UNAVAILABLE')
        self.assertTrue(got['no_literature_absence_claim'])

    def test_pdf_size_cap(self):
        rec={'doi':DOI,'title':TITLE,'best_oa_pdf_url':PUBLIC_URL}
        got=oa_pdf.read_from_openalex_record({'doi':DOI,'page':1},rec,lambda _:b'%PDF-'+b'x'*oa_pdf.MAX_PDF_BYTES)
        self.assertEqual(got['status'],'EVIDENCE_UNAVAILABLE')

if __name__=='__main__':unittest.main(verbosity=2)
