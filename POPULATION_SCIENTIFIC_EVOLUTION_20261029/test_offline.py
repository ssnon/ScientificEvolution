#!/usr/bin/env python3
"""Offline fixtures for prefix forking, model provenance, and lineage math.
Not a paid WSL end-to-end test; repository-native preflight is still required.
"""
from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from dataclasses import dataclass
import population_run as p


def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()

@dataclass
class FakeState:
    program: dict
    assets:dict
    model_calls:dict

class FakeJournal:
    def __init__(self,root):self.root=Path(root)
    def _events(self):
        rows=[json.loads(x.read_bytes()) for x in sorted((self.root/'events').glob('*.json'))]
        old=None
        for ix,row in enumerate(rows,1):
            assert row['seq']==ix and row['prev']==old
            assert (self.root/'events'/f'{ix:08d}.json').read_bytes()==canon(row)
            old=sha(canon(row))
        return rows
    def verify(self):
        rows=self._events()
        for f in (self.root/'blobs').iterdir():assert f.name==sha(f.read_bytes())
        for row in rows:
            for k,v in row['payload'].items():
                if k in p.BLOB_KEYS:assert (self.root/'blobs'/v).exists()
        return FakeState({'problem':'P0 test question'}, {}, {})


def make_root(root):
    (root/'events').mkdir(parents=True);(root/'blobs').mkdir()
    (root/'manifest.json').write_bytes(canon({'protocol':'E2_AUTONOMOUS_EVOLUTION_V1'}))
    history=[('PROGRAM_CREATED',{'problem':'P0 test question'}),('SOURCE_REGISTERED',{})]
    old=None
    for i,(kind,payload) in enumerate(history,1):
        if i==2:
            content=canon({'text':'historical evidence'})
            dig=sha(content);(root/'blobs'/dig).write_bytes(content)
            payload={'id':'SRC_X','kind':'HISTORICAL_AI','blob':dig}
        item={'seq':i,'prev':old,'kind':kind,'protocol':'E2_AUTONOMOUS_EVOLUTION_V1','payload':payload}
        b=canon(item);(root/'events'/f'{i:08d}.json').write_bytes(b);old=sha(b)
    # A future response blob exists in original but must not enter the fork.
    future=canon({'future':'science from after checkpoint'})
    (root/'blobs'/sha(future)).write_bytes(future)
    item={'seq':3,'prev':old,'kind':'MODEL_CALL_INTENT','protocol':'E2_AUTONOMOUS_EVOLUTION_V1',
          'payload':{'id':'CTRL_D00001','request_blob':sha(future)}}
    (root/'events'/'00000003.json').write_bytes(canon(item))
    return sha(canon(json.loads((root/'events'/'00000002.json').read_text())))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp);src=base/'source';expect=make_root(src)
        mods=SimpleNamespace(J=FakeJournal,canon=canon,sha=sha)
        rec=p.clone_at_checkpoint(mods,src,base/'peer_A',2,expect)
        assert rec['events']==2
        assert len(list((base/'peer_A'/'blobs').iterdir()))==1
        assert len(list((src/'blobs').iterdir()))==2
        assert len(list((src/'events').iterdir()))==3
        assert FakeJournal(base/'peer_A')._events()[-1]['seq']==2
        try:p.clone_at_checkpoint(mods,src,base/'wrong',2,'f'*64)
        except RuntimeError as e:assert 'HASH_MISMATCH' in str(e)
        else:raise AssertionError('Hash mismatch must fail closed')
        try:p.clone_at_checkpoint(mods,src,base/'peer_A',2,expect)
        except RuntimeError as e:assert 'DEST_EXISTS' in str(e)
        else:raise AssertionError('No overwrite permitted')
    # Verify that transitive G0 and peer-import ancestry are distinct from
    # generic parent links.
    assets={
       'A_ISO_old':{'origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK','parent_ids':[]},
       'A_PEER_new':{'origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK','parent_ids':['A_ISO_old']},
       'A_LIVE_next':{'parent_ids':['A_PEER_new']},
       'A_LIVE_local':{'parent_ids':[]},
    }
    base,hits=p.ancestry(SimpleNamespace(assets=assets))
    assert 'A_ISO_old' in base and hits('A_LIVE_next') and not hits('A_LIVE_local')
    print('PASS: prefix replay hashes; future-blob isolation; no-overwrite; transitive parent graph')
if __name__=='__main__':main()
