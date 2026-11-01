"""M21: bounded, DOI-bound OA PDF inspection. No user-supplied URLs or model instructions.

Entry point is read_from_openalex_record(...). OA candidate URLs come exclusively
from a DOI-exact OpenAlex resolve, not from a Worker-provided URL. This module
provides a separate constrained HTTPS fetcher for OA hosts. No source is a
scientific certificate; text extraction cannot inspect images/tables reliably.
"""
from __future__ import annotations
import hashlib
import http.client
import io
import ipaddress
import re
import socket
import ssl
from urllib.parse import urlsplit, urljoin

MAX_PDF_BYTES = 7_500_000
MAX_PAGES = 400
MAX_HOPS = 3
MAX_CANDIDATES = 6
MAX_PAGE_TEXT = 10_000

class OAPDFError(ValueError):
    pass

class PDFBytes(bytes):
    """Transport result with separately retained redirect provenance."""


def checked_public_https_url(url):
    """Never accept private IPs, bare hosts, credentials, ports, or non-HTTPS."""
    if not isinstance(url, str) or not 1 <= len(url) <= 1600 or any(ord(c)<33 for c in url) or '\\' in url:
        raise OAPDFError('UNSAFE_OA_URL')
    try:
        p = urlsplit(url)
        host = (p.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
    except (ValueError, UnicodeError):
        raise OAPDFError('INVALID_OA_HOST')
    if (p.scheme != 'https' or p.username is not None or p.password is not None
            or p.port not in (None, 443) or not re.fullmatch(r'[a-z0-9.-]{4,253}', host)
            or '..' in host or host.startswith('-') or host.endswith('-')
            or '.' not in host or len(host.split('.')[-1]) < 2
            or any(label.startswith('-') or label.endswith('-') or len(label)>63 for label in host.split('.'))
            or host.endswith(('.local','.localhost','.internal','.lan','.test','.invalid','.onion','.arpa'))):
        raise OAPDFError('UNSAFE_OA_HOST_OR_SCHEME')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise OAPDFError('IP_LITERAL_NOT_ALLOWED')
    if p.fragment:raise OAPDFError('URL_FRAGMENT_NOT_ALLOWED')
    if any(c in (p.path or '') for c in '\r\n') or any(c in (p.query or '') for c in '\r\n'):
        raise OAPDFError('URL_CRLF_NOT_ALLOWED')
    return host, (p.path or '/') + (('?' + p.query) if p.query else '')


def _checked_dns(host):
    """Verify every returned A/AAAA record; connection then pins an approved IP."""
    try: rows=socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:raise OAPDFError('OA_DNS_LOOKUP_FAILED')
    if not rows or len(rows)>40:raise OAPDFError('OA_DNS_ANSWER_INVALID')
    for family,kind,proto,canon,sockaddr in rows:
        if family not in (socket.AF_INET,socket.AF_INET6) or not ipaddress.ip_address(sockaddr[0]).is_global:
            raise OAPDFError('NONPUBLIC_OA_DNS_ADDRESS')
    return rows


def _one_request(url):
    host, target = checked_public_https_url(url)
    addresses = _checked_dns(host)
    context=ssl.create_default_context()
    conn=http.client.HTTPSConnection(host,port=443,timeout=18,context=context)
    def pinned_connect():
        last = None
        for family,kind,proto,canon,sockaddr in addresses:
            sock=socket.socket(family,kind,proto)
            sock.settimeout(18)
            try:
                sock.connect(sockaddr)
                conn.sock=context.wrap_socket(sock,server_hostname=host)
                return
            except (OSError,ssl.SSLError) as exc:
                last=exc
                sock.close()
        raise OAPDFError('VERIFIED_PUBLIC_OA_CONNECT_FAILED') from last
    conn.connect=pinned_connect
    try:
        conn.request('GET',target,headers={
            'Host':host,'User-Agent':'ScientificEvolution-M21/1.0 (OA research)',
            'Accept':'application/pdf,application/octet-stream;q=0.5',
            'Accept-Encoding':'identity','Connection':'close'})
        response=conn.getresponse()
        code=response.status
        location=response.getheader('Location')
        content_type=(response.getheader('Content-Type') or '')[:120]
        if code in (301,302,303,307,308):
            return {'status':code,'location':location,'body':b'','content_type':content_type}
        if code!=200:raise OAPDFError('OA_HTTP_STATUS_'+str(code))
        size=response.getheader('Content-Length')
        if size and size.isdigit() and int(size)>MAX_PDF_BYTES:raise OAPDFError('OA_PDF_TOO_LARGE')
        if response.getheader('Content-Encoding') not in (None,'identity'):
            raise OAPDFError('OA_ENCODING_UNSUPPORTED')
        body=response.read(MAX_PDF_BYTES+1)
        if len(body)>MAX_PDF_BYTES:raise OAPDFError('OA_PDF_TOO_LARGE')
        return {'status':code,'location':None,'body':body,'content_type':content_type}
    except (OSError,ssl.SSLError,http.client.HTTPException) as exc:
        raise OAPDFError('OA_HTTP_TRANSPORT_FAILURE') from exc
    finally:conn.close()


def public_pdf_get(url):
    """GET an OpenAlex-derived OA candidate, revalidating each redirect hop."""
    chain=[]; seen=set()
    for hop in range(MAX_HOPS+1):
        checked_public_https_url(url)
        if url in seen:raise OAPDFError('OA_REDIRECT_LOOP')
        seen.add(url)
        response=_one_request(url)
        chain.append({'url':url,'http_status':response['status']})
        if response['status']==200:
            result=PDFBytes(response['body'])
            result.redirect_chain=chain
            result.content_type=response['content_type']
            return result
        if hop==MAX_HOPS:raise OAPDFError('OA_REDIRECT_LIMIT')
        destination=response['location']
        if not isinstance(destination,str) or not destination.strip():raise OAPDFError('OA_REDIRECT_NO_LOCATION')
        url=urljoin(url,destination.strip())
    raise OAPDFError('OA_REDIRECT_LIMIT')


def _title_tokens(text):
    return [x for x in re.findall(r'[a-z0-9]+',text.lower()) if len(x)>2]


def _identity_ok(text, title, doi):
    """Conservative text-layer title matching; DOI alone is not authoritative."""
    tokens=_title_tokens(title)
    if len(tokens)<5:return False,0.0
    norm=set(_title_tokens(text[:25_000]))
    score=sum(1 for t in set(tokens) if t in norm)/len(set(tokens))
    return score>=0.78,round(score,3)


def candidate_urls(record):
    if not isinstance(record,dict):raise OAPDFError('BAD_OA_RECORD')
    urls=[]
    for key in ('best_oa_pdf_url','best_oa_landing_url'):
        if isinstance(record.get(key),str) and record[key]:urls.append(record[key])
    for loc in record.get('other_oa_locations',[]):
        if isinstance(loc,dict):
            for key in ('pdf_url','landing_page_url'):
                if isinstance(loc.get(key),str) and loc[key]:urls.append(loc[key])
    found=[]
    for url in urls:
        if url not in found:found.append(url)
    # Prefer actual PDF paths and verified public repositories over DOI redirectors.
    def preference(url):
        u=urlsplit(url)
        return (0 if u.path.lower().endswith('.pdf') else 1,
                1 if (u.hostname or '').lower() in ('doi.org','dx.doi.org') else 0)
    return sorted(found,key=preference)[:MAX_CANDIDATES]


def read_from_openalex_record(args,record,fetch):
    """Fetch PDF candidate(s), check identity, extract bounded page with provenance.

    fetch receives only candidate URLs derived from a DOI-exact OpenAlex resolve.
    In real mode fetch uses public_pdf_get; offline tests inject a fake fetch.
    """
    doi=args.get('doi')
    if not isinstance(doi,str) or doi.lower()!=str(record.get('doi','')).lower():
        return {'status':'REJECTED','error_code':'OPENALEX_DOI_IDENTITY_MISMATCH',
                'evidence_class':'NO_EVIDENCE_RETRIEVED'}
    page=args.get('page',1)
    if type(page) is not int or not 1<=page<=MAX_PAGES:
        return {'status':'REJECTED','error_code':'INVALID_PAGE','evidence_class':'NO_EVIDENCE_RETRIEVED'}
    tried=[]
    # Optional Worker-discovered lead, not a special-case URL or DOI. It gets
    # precisely the same public-host, bounded PDF and title checks as OA URLs.
    suggested=args.get('candidate_url')
    if suggested is not None and not isinstance(suggested,str):
        return {'status':'REJECTED','error_code':'INVALID_CANDIDATE_URL',
                'evidence_class':'NO_EVIDENCE_RETRIEVED'}
    urls=([suggested] if suggested else []) + candidate_urls(record)
    urls=list(dict.fromkeys(urls))[:MAX_CANDIDATES+1]
    for url in urls:
        try:
            checked_public_https_url(url)
            raw=fetch(url)
            if not isinstance(raw,bytes) or len(raw)>MAX_PDF_BYTES or not raw.startswith(b'%PDF-'):
                raise OAPDFError('NOT_BOUNDED_PDF_BYTES')
            try:
                from pypdf import PdfReader
            except ImportError:raise OAPDFError('PYPDF_DEPENDENCY_MISSING')
            try:
                reader=PdfReader(io.BytesIO(raw),strict=False)
                if reader.is_encrypted:raise OAPDFError('OA_PDF_ENCRYPTED')
                if not 1<=len(reader.pages)<=MAX_PAGES:raise OAPDFError('OA_PDF_PAGE_COUNT_UNSUPPORTED')
                # Identity verified using text layer of the first one or two pages.
                samples=[]
                for i in range(min(2,len(reader.pages))):
                    samples.append((reader.pages[i].extract_text() or '')[:12000])
                text='\n'.join(samples)
                matched,score=_identity_ok(text,record.get('title',''),doi)
                if not matched:raise OAPDFError('OA_PDF_TITLE_IDENTITY_UNVERIFIED')
                if page>len(reader.pages):raise OAPDFError('OA_PDF_PAGE_OUT_OF_RANGE')
                page_text=(reader.pages[page-1].extract_text() or '')[:MAX_PAGE_TEXT]
                if not page_text.strip():raise OAPDFError('OA_PDF_PAGE_NO_EXTRACTED_TEXT')
            except OAPDFError:raise
            except Exception as exc:raise OAPDFError('OA_PDF_PARSER_FAILED') from exc
            chain=getattr(raw,'redirect_chain',[{'url':url,'http_status':200}])
            return {'status':'DELIVERED','action':'read_oa_pdf','doi':doi,
                'title':record.get('title'),'source_url':chain[-1]['url'],
                'candidate_url':url,'redirect_chain':chain,
                'candidate_provenance':('WORKER_SUGGESTED_UNVERIFIED_URL_PDF_TITLE_CHECKED'
                                        if suggested and url==suggested else 'DOI_MATCHED_OPENALEX_METADATA'),
                'source_sha256':hashlib.sha256(raw).hexdigest(),'document_bytes':len(raw),
                'page':page,'page_count':len(reader.pages),'page_text':page_text,
                'title_token_coverage':score,'identity_verification':'MATCHED_OPENALEX_DOI_AND_PDF_TITLE_TEXT',
                'evidence_class':'OA_PDF_TEXT','text_extracted':True,
                'image_figure_table_contents_verified':False,
                'scientific_certification':False,
                'warning':'PDF text is source material, not verified science; equations/images/tables may be lost.'}
        except (OAPDFError,OSError,ValueError) as ex:
            tried.append({'candidate_url':url,'error_code':str(ex)[:85]})
    return {'status':'EVIDENCE_UNAVAILABLE','action':'read_oa_pdf','doi':doi,
        'evidence_class':'NO_EVIDENCE_RETRIEVED','candidate_attempts':tried,
        'reason':'NO_SAFE_IDENTITY_MATCHED_OA_PDF_TEXT',
        'no_literature_absence_claim':True,'scientific_certification':False}
