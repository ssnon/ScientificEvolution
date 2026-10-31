#!/usr/bin/env python3
"""Public article retrieval audit, read-only, no model calls. Downloads solely designated public primary sources."""
import argparse,hashlib,html,json,re,urllib.request,urllib.error,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

URLS={
 'europepmc_xml':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4129422/fullTextXML',
 'nature_html':'https://www.nature.com/articles/srep05940',
}
PATTERNS={
 'fig3':'Figure 3',
 'lipid_shifts':'Raman vibrations',
 'uncorrelated_lines':'uncorrelated to other Raman',
 'anticorrelation':'anti-correlat',
 'time_resolution':'acquisition time',
 'single_molecule_caveat':'blinking',
 'vibrational_mechanism':'vibronic coupling',
}
class Stripper(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag.lower() in ('script','style'): self.skip+=1
 def handle_endtag(self,tag):
  if tag.lower() in ('script','style') and self.skip:self.skip-=1
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)

def inspect(label,url,timeout):
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ScientificEvolution-public-source-audit/1.0 (+noncommercial)'} )
  with urllib.request.urlopen(req,timeout=timeout) as r:
   content=r.read(8_000_001);code=r.status; final_url=r.url
  if len(content)>8_000_000:raise ValueError('MAX_BYTES_EXCEEDED')
  try:
   if label.endswith('xml'): t=' '.join(ET.fromstring(content).itertext())
   else:
    parser=Stripper();parser.feed(content.decode('utf-8',errors='replace'));t=' '.join(parser.parts)
  except Exception as exc:raise ValueError('PARSE_FAILED:'+repr(exc))
  t=re.sub(r'\s+',' ',html.unescape(t)).strip()
  if len(t)<1000 or 'Checking your browser' in t[:500]:raise ValueError('BLOCKED_OR_TRUNCATED_RESPONSE')
  matches={}
  for k,pat in PATTERNS.items():
   m=re.search(re.escape(pat),t,re.IGNORECASE)
   matches[k]={'found':bool(m),'brief_context':t[max(0,m.start()-100):m.end()+180] if m else None}
  return {'provider':label,'requested_url':url,'resolved_url':final_url,'http_status':code,
          'sha256_raw':hashlib.sha256(content).hexdigest(),'bytes_raw':len(content),
          'characters_extracted':len(t),'patterns':matches}
 except Exception as ex:return {'provider':label,'requested_url':url,'error':repr(ex)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--timeout',type=int,default=25)
 a=p.parse_args();out=a.out.expanduser().absolute()
 if out.exists():raise FileExistsError('OUTPUT_EXISTS:'+str(out))
 reports=[inspect(label,url,a.timeout) for label,url in URLS.items()]
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({'article':'Taylor et al., Scientific Reports 4:5940 (2014)','doi':'10.1038/srep05940',
  'pmcid':'PMC4129422','status':'RETRIEVAL_AND_TEXT_AUDIT_ONLY_NOT_SCIENCE_CERTIFICATION','retrievals':reports},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'saved':str(out),'retrievals':[{'provider':x['provider'],'error':x.get('error'),
   'sha256_raw':x.get('sha256_raw'),'matched':sum(int(y['found']) for y in x.get('patterns',{}).values())}
   for x in reports]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
