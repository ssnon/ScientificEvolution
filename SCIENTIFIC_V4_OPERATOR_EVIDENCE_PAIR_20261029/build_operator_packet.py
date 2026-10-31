#!/usr/bin/env python3
"""Convert an existing on-disk, executed retrieval audit into a typed operator evidence packet.

No new web request, LLM or science conclusion. Snippets are verbatim normalized
text windows extracted by the earlier user-run check_pmc_source.py.
"""
import argparse, hashlib, json
from pathlib import Path

KEYS = ('fig3','lipid_shifts','uncorrelated_lines','anticorrelation',
        'time_resolution','single_molecule_caveat','vibrational_mechanism')
EXPECTED_DOI = '10.1038/srep05940'
EXPECTED_PMCID = 'PMC4129422'

def create(audit):
    assert audit.get('pmcid') == EXPECTED_PMCID and audit.get('doi') == EXPECTED_DOI, 'UNEXPECTED_PAPER'
    by_provider = {x['provider']:x for x in audit['retrievals']}
    assert {'europepmc_xml','nature_html'} <= set(by_provider), 'MISSING_INDEPENDENT_RETRIEVAL'
    for label in ('europepmc_xml','nature_html'):
        p = by_provider[label]
        assert not p.get('error') and p.get('http_status') == 200, 'RETRIEVAL_FAILED:'+label
        assert len(p['sha256_raw']) == 64, 'MISSING_RAW_CONTENT_HASH:'+label
    source = by_provider['europepmc_xml']
    items=[]
    for key in KEYS:
        m=source['patterns'].get(key,{})
        assert m.get('found') and isinstance(m.get('brief_context'),str), 'UNVERIFIED_PATTERN:'+key
        snippet=' '.join(m['brief_context'].split())
        assert len(snippet)>100, 'CONTEXT_TOO_SHORT:'+key
        items.append({
            'id':'PMC4129422_'+key.upper(),
            'inspection_class':'DIRECT_FULLTEXT_EXCERPT',
            'title':'Watching individual molecules flex within lipid membranes using SERS',
            'locator':'Europe PMC fullTextXML parsed-text window around audit search key: '+key,
            'origin_url_or_doi':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4129422/fullTextXML',
            'excerpt':snippet,
            'inspection_method':('Operator-directed public-text retrieval by user-executed '
                'check_pmc_source.py; normalized XML itertext matched literal search key; '
                'no AI autonomous literature discovery in this trial'),
            'scope_limits':('VERBATIM LOCAL CONTEXT WINDOW ONLY, NOT FULL FIGURE OR FULL ARTICLE. '
                'Selection by operator/authored keyword. Retrieved raw XML SHA256='+source['sha256_raw']+
                '; Nature cross-check SHA256='+by_provider['nature_html']['sha256_raw']+
                '. The context does not by itself establish causal mechanism, novelty, or physical correctness.')
        })
    return {'records':items}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--audit',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    assert args.audit.is_file(), 'AUDIT_FILE_MISSING'
    assert not args.out.exists(), 'REFUSE_OVERWRITE'
    raw=args.audit.read_bytes(); packet=create(json.loads(raw))
    # Validate against the exact installed scientific input contract when accessible.
    try:
        from scientific_problem_evolution import validate_packet
        validate_packet(packet)
        validated='MATCHES_INSTALLED_V4_CONTRACT'
    except ModuleNotFoundError:
        validated='STRUCTURAL_CHECK_ONLY_INSTALL_REPO_PYTHONPATH_TO_VALIDATE'
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'packet':str(args.out),'entries':len(packet['records']),
       'operator_directed':True,'audit_sha256':hashlib.sha256(raw).hexdigest(),
       'contract_validation':validated,'no_science_certification':True},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
