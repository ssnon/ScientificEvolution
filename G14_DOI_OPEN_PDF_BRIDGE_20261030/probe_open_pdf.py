#!/usr/bin/env python3
"""Optional no-provider-request diagnostic, touches NO E2 Journals.
Queries bibliographic endpoint and publicly accessible PDF only.
"""
import argparse, json
import doi_open_pdf

p=argparse.ArgumentParser()
p.add_argument('--doi',required=True)
p.add_argument('--page',type=int,default=1)
p.add_argument('--out')
a=p.parse_args()
r=doi_open_pdf.read_open_pdf({'doi':a.doi,'page':a.page})
summary={k:v for k,v in r.items() if k!='page_text'}
summary['page_text_excerpt']=(r.get('page_text') or '')[:1300]
summary['provider_requests_sent']=0
summary['journal_modified']=False
if a.out:
    with open(a.out,'x',encoding='utf8') as f:
        json.dump(r,f,ensure_ascii=False,indent=2)
print(json.dumps(summary,ensure_ascii=False,indent=2))
