#!/usr/bin/env python3
"""DOI-scoped public-PDF retrieval; never accepts model-authored URLs.

Metadata is not evidence of content. A vetted domain and a PDF that matches
its DOI/title are required for OA_PDF_TEXT. This does not certify scientific claims.
"""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import resource
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_PDF_BYTES = 8_000_000
MAX_TEXT = 9500
DOI_RE = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\Z', re.I)
# Explicit host allowlist. OpenAlex discovery by itself does NOT authorize a host.
# Expand only after inspecting the publisher/repository, never via a model URL.
APPROVED_PDF_HOSTS = frozenset({
    'www.columbia.edu', 'columbia.edu',
    'repository.upenn.edu', 'pubs.acs.org',
    'www.spiedigitallibrary.org', 'spiedigitallibrary.org',
    'iopscience.iop.org', 'link.springer.com',
    'static-content.springer.com', 'www.nature.com',
    'arxiv.org', 'hal.science', 'zenodo.org',
    'www.rsc.org', 'onlinelibrary.wiley.com',
    'eprints.soton.ac.uk', 'eprints.whiterose.ac.uk',
    'pmc.ncbi.nlm.nih.gov',
})
# Author-hosted locator grounded in a public author-group copy of this DOI.
# This is ONLY a location pointer, not a supplied science claim or a read receipt.
# SYN_01 already independently chose this exact DOI before this mapping existed.
REVIEWED_LOCATORS = {
    '10.1021/jp034632u': [
        {'url':'https://www.columbia.edu/cu/chemistry/groups/brus/pdf2/jp034632u.pdf',
         'locator_class':'OPERATOR_REVIEWED_AUTHOR_HOSTED_LOCATION_NOT_PRIOR_SCIENCE',
         'verified_article_locator':'https://doi.org/10.1021/jp034632u'}
    ]
}

class RetrievalLimit(Exception):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kw):
        raise RetrievalLimit('REDIRECT_DISALLOWED')


def _urlcheck(url, is_metadata=False):
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or '').lower().rstrip('.')
    if (u.scheme != 'https' or not host or u.port is not None
            or u.username is not None or u.password is not None
            or u.fragment or not u.path or '\\' in url):
        raise RetrievalLimit('URL_NOT_ALLOWED')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise RetrievalLimit('IP_LITERAL_DISALLOWED')
    allowed = host == 'api.openalex.org' if is_metadata else host in APPROVED_PDF_HOSTS
    if not allowed:
        raise RetrievalLimit('METADATA_HOST_NOT_APPROVED' if is_metadata else 'PDF_HOST_NOT_APPROVED')
    if is_metadata and not u.path.startswith('/works/'):
        raise RetrievalLimit('METADATA_PATH_NOT_ALLOWED')
    if len(url) > 1000:
        raise RetrievalLimit('URL_TOO_LONG')
    return host


def _checked_public_dns(host):
    """Prevent obvious private-address DNS answers; allowlist and TLS are primary boundaries.

    Check-before-connect is not DNS pinning, so not a general arbitrary-URL SSRF defense.
    """
    for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise RetrievalLimit('NONPUBLIC_DNS_ADDRESS')


def network_fetch(url, *, is_metadata=False):
    host = _urlcheck(url, is_metadata)
    _checked_public_dns(host)
    opener = urllib.request.build_opener(
        NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    request = urllib.request.Request(url, headers={
        'User-Agent':'ScientificEvolution-DOI-Evidence/1.0 (noncommercial research)',
        'Accept':'application/json' if is_metadata else 'application/pdf,application/octet-stream'})
    try:
        with opener.open(request, timeout=20) as r:
            if r.status != 200:
                raise RetrievalLimit('HTTP_NON_200')
            size = int(r.headers.get('Content-Length') or 0)
            limit = 500_000 if is_metadata else MAX_PDF_BYTES
            if size > limit:
                raise RetrievalLimit('REMOTE_DOCUMENT_TOO_LARGE')
            data = r.read(limit+1)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise RetrievalLimit('REMOTE_HTTP_OR_NETWORK_FAILURE:'+str(getattr(exc,'code',type(exc).__name__))) from exc
    if len(data) > limit:
        raise RetrievalLimit('DOCUMENT_TOO_LARGE')
    return data


def _canon_doi(doi):
    if not isinstance(doi,str) or len(doi)>220 or not DOI_RE.fullmatch(doi.strip()):
        raise RetrievalLimit('INVALID_DOI')
    return doi.strip().lower()


def _openalex(doi, fetch):
    url = 'https://api.openalex.org/works/https://doi.org/'+urllib.parse.quote(doi, safe='/')
    raw = fetch(url, is_metadata=True)
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise RetrievalLimit('INVALID_OPENALEX_JSON') from exc
    if not isinstance(data,dict):
        raise RetrievalLimit('INVALID_OPENALEX_RECORD')
    indexed_doi = str(data.get('doi') or '').lower().removeprefix('https://doi.org/')
    if indexed_doi != doi:
        raise RetrievalLimit('DOI_METADATA_IDENTITY_MISMATCH')
    title = str(data.get('display_name') or '')
    if len(title)<16:
        raise RetrievalLimit('DOI_METADATA_MISSING_TITLE')
    return data, title, url


def _candidates(doi, record):
    # Reviewed exact-DOI author PDF is a locator only, not an instruction to read
    # a particular scientific paper or a claim about its contents.
    seen=set(); result=[]
    for item in REVIEWED_LOCATORS.get(doi,[]):
        url=item['url'];seen.add(url)
        result.append({'url':url,'origin':item['locator_class'],
                       'association':'REVIEWED_EXACT_DOI_LOCATOR'})
    locations = ([record.get('best_oa_location')] + list(record.get('locations') or []))
    for loc in locations:
        if not isinstance(loc,dict) or not loc.get('is_oa'):
            continue
        for key in ('pdf_url',):
            url=loc.get(key)
            if not isinstance(url,str) or url in seen or not url:continue
            seen.add(url)
            result.append({'url':url,'origin':'OPENALEX_DOI_OA_LOCATION',
                           'association':'EXTERNAL_INDEX_METADATA_NOT_SOURCE_VALIDATION'})
    return result[:10]


def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (1024*1024*1024,1024*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU, (14,14))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0,0))


def _extract(pdf, page):
    child = Path(__file__).with_name('pdf_extract_child.py')
    try:
        p=subprocess.run([sys.executable,str(child),str(page)],input=pdf,
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         timeout=22,check=False,preexec_fn=_limits)
    except subprocess.TimeoutExpired as exc:
        raise RetrievalLimit('PDF_EXTRACTION_TIMEOUT') from exc
    if p.returncode or len(p.stdout)>130_000:
        raise RetrievalLimit('PDF_EXTRACTION_FAILED')
    try:
        obj=json.loads(p.stdout)
    except ValueError as exc:
        raise RetrievalLimit('PDF_EXTRACTION_INVALID_JSON') from exc
    if 'error' in obj or not obj.get('page_text','').strip():
        raise RetrievalLimit('PDF_PAGE_NOT_TEXT_EXTRACTABLE')
    return obj


def _tokens(value):
    ignore={'the','and','with','from','that','this','into','for','of','at','in','on','to','by','a','an'}
    return {x for x in re.findall(r'[a-z0-9]{3,}',value.lower()) if x not in ignore}


def _check_identity(doi,title,first_pages):
    a=_tokens(title);b=_tokens(first_pages)
    coverage=len(a&b)/max(1,len(a))
    doi_hit = doi.lower() in first_pages.lower().replace(' ','').replace('\n','')
    if len(a)<3 or coverage < 0.68:
        raise RetrievalLimit('PDF_TITLE_DOES_NOT_MATCH_DOI_METADATA')
    return {'basis':'PDF_FIRST_TWO_PAGES_TITLE_AND_DOI' if doi_hit else 'PDF_FIRST_TWO_PAGES_TITLE',
            'title_token_coverage':round(coverage,4),'doi_printed_in_extracted_text':doi_hit,
            'identity_is_not_experimental_claim_verification':True}


def read_open_pdf(args, fetch=network_fetch, extract=_extract):
    """Resolve a DOI to an approved public PDF and read ONE page with provenance.

    Use an injected fetch for offline tests; never try a model-supplied URL.
    """
    try:
        if not isinstance(args,dict) or set(args)-{'doi','page'}:
            raise RetrievalLimit('INVALID_ARGUMENTS_ONLY_DOI_AND_PAGE')
        doi=_canon_doi(args.get('doi'))
        page=args.get('page',1)
        if type(page) is not int or not 1<=page<=200:
            raise RetrievalLimit('INVALID_PAGE')
        record,title,meta_url=_openalex(doi,fetch)
        choices=_candidates(doi,record)
        if not choices:
            raise RetrievalLimit('NO_DOI_LINKED_PUBLIC_PDF_LOCATOR')
        attempts=[]
        for candidate in choices[:4]:
            url=candidate['url']
            try:
                _urlcheck(url)
                raw=fetch(url,is_metadata=False)
                if not raw.startswith(b'%PDF-'):
                    raise RetrievalLimit('RESPONSE_NOT_PDF_MAGIC')
                d=extract(raw,page)
                identity=_check_identity(doi,title,d['first_text'])
                text=d['page_text'][:MAX_TEXT]
                return {'status':'DELIVERED','action':'read_open_pdf',
                    'doi':doi,'title_from_doi_index':title,'page':page,
                    'page_count':d['page_count'],'page_text':text,
                    'page_text_sha256':hashlib.sha256(text.encode('utf8')).hexdigest(),
                    'source_url':url,'source_sha256':hashlib.sha256(raw).hexdigest(),
                    'document_bytes':len(raw),'source_association':candidate['association'],
                    'locator_origin':candidate['origin'],'metadata_url':meta_url,
                    'doi_pdf_identity_check':identity,'evidence_class':'OA_PDF_TEXT',
                    'scientific_certification':False,
                    'document_license_not_independently_verified':True,
                    'full_pdf_not_returned_to_model':True,
                    'pdf_figures_not_visually_inspected':True,
                    'retrieval_attempts':attempts+[{'kind':'PDF','source_url':url,'result':'DELIVERED'}]}
            except (RetrievalLimit, OSError, ValueError) as exc:
                attempts.append({'kind':'PDF','source_url':url,'result':'RETRIEVAL_FAILED',
                                 'reason':str(exc)[:140]})
        return {'status':'EVIDENCE_UNAVAILABLE','action':'read_open_pdf','doi':doi,
            'error_code':'DOI_PUBLIC_PDF_CANDIDATES_UNAVAILABLE_OR_UNVERIFIED',
            'retrieval_attempts':attempts,'empirical_evidence_retrieved':False,
            'availability_not_evidence_of_scientific_absence':True,
            'scientific_certification':False}
    except (RetrievalLimit,OSError,ValueError) as exc:
        return {'status':'REJECTED' if str(exc).startswith(('INVALID_','DOI_METADATA_IDENTITY_MISMATCH')) else 'EVIDENCE_UNAVAILABLE',
            'action':'read_open_pdf','error_code':str(exc)[:150],
            'empirical_evidence_retrieved':False,
            'availability_not_evidence_of_scientific_absence':True,
            'scientific_certification':False}
