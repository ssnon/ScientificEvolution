"""M25 no-paid integration tests for the inherited peer-reader and new native source pin."""
from __future__ import annotations
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from e2core.core import EvolutionJournal
import generational_run as gen
import persistent_population as pp
import population_resume as compat

class TestM25TransferGate(unittest.TestCase):
    def test_real_historical_peer_compatibility_payload_has_m25_outcome(self):
        with tempfile.TemporaryDirectory(prefix='m25_peer_compat_') as td:
            root=Path(td)/'journal'
            j=EvolutionJournal(root)
            j.init('P0 scientific hypothesis')
            sid='SRC_PEER_DECISION_SYN_01'
            j.add_source(sid,'HISTORICAL_AI',{
                'original_root':'/historical/donor',
                'decisions':[{'id':'D00001','rationale':'conditional critique'}],
                'new_assets':[], 'asset_id_translation':{}, 'opportunity_assessments':[]},
                'Synthetic independent PEER judgements, not observations')
            work={'id':'W_M25_PEER_READER','mode':'INFORMED','problem_id':'P0',
                  'question':'Inspect transferred PEER reasoning and decide whether to continue',
                  'research_rationale':'Audit inherited PEER model reasoning without treating it as evidence',
                  'source_ids':[sid]}
            j.evolve('E_M25_PEER_READER','REFRAME',[],work,'Legitimate independently chosen peer-reading Work')
            j.start('W_M25_PEER_READER')
            mods=gen.modules()
            with compat.historical_input_compat(mods,root):
                data=mods.spe._ORIGINAL_WORKER_INPUT(j,'W_M25_PEER_READER','NATIVE_RESEARCH_TOOLS')
            self.assertIn('m25_own_observed_work_outcome',data)
            own=data['m25_own_observed_work_outcome']
            self.assertEqual(own['work_id'],'W_M25_PEER_READER')
            self.assertEqual(own['actual_tool_count'],0)
            self.assertEqual(own['scientific_question_resolved'],'NOT_DETERMINED_BY_OPERATIONAL_LEDGER')
            self.assertEqual(data['pinned_input']['work']['mode'],'INFORMED')
            self.assertTrue(data['pinned_input']['authorized_historical_records'])
            self.assertEqual(data['pinned_input']['authorized_historical_records'][0]['tool_status'],'NO_NEW_TOOL_EXECUTION')

    def test_normal_persistent_init_creates_and_verifies_source_pin(self):
        with tempfile.TemporaryDirectory(prefix='m25_native_pin_') as td:
            src=Path(td)/'source_root'
            j=EvolutionJournal(src)
            j.init('P0 scientific hypothesis to be carried without execution')
            new=Path(td)/'new_experiment'
            from e2core.activation_contract import PROTOCOL, DEFAULTS
            profile_file=Path(td)/'explicit_activation.json'
            profile_file.write_text(json.dumps({
                'protocol':PROTOCOL,'model':'openai/gpt-5.6-luna',
                'purpose':'Synthetic root source pin regression',
                'features':dict(DEFAULTS)}))
            args=SimpleNamespace(source_root=str(src),out=str(new),
                math_verification=False,activation_profile=str(profile_file))
            from unittest.mock import patch
            with patch.dict('os.environ', dict(DEFAULTS)):
                with contextlib.redirect_stdout(io.StringIO()):
                    pp.init(args)
            pin=new/gen.NATIVE_PIN_NAME
            self.assertTrue(pin.is_file(),'normal init must pin its own new source root')
            content=json.loads(pin.read_text())
            self.assertEqual(content['protocol'],gen.NATIVE_SOURCE_PROTOCOL)
            self.assertTrue(content['files'])
            self.assertEqual(gen.verify_runtime_source(gen.modules(),new/'BASE_000')['source_contract'],gen.NATIVE_SOURCE_PROTOCOL)

if __name__=='__main__':unittest.main(verbosity=2)
