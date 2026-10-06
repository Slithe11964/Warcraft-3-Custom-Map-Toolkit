"""Portable study-pipeline smoke tests using synthetic JASS archives only."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from mpq import MPQ, encrypt, hash_string, write_files
from add_header import build_header
from deprotect import rename_generated

SCRIPT = '''globals
trigger gg_trg_Sample=null
integer udg_Counter=0
endglobals
function Trig_Sample_Actions takes nothing returns nothing
set udg_Counter=udg_Counter+1
endfunction
function InitTrig_Sample takes nothing returns nothing
set gg_trg_Sample=CreateTrigger()
call TriggerRegisterTimerEvent(gg_trg_Sample,1.,true)
call TriggerAddAction(gg_trg_Sample,function Trig_Sample_Actions)
endfunction
function InitCustomTriggers takes nothing returns nothing
call InitTrig_Sample()
endfunction
function main takes nothing returns nothing
call InitBlizzard()
call InitCustomTriggers()
endfunction
function config takes nothing returns nothing
call SetPlayers(1)
endfunction
'''

def fixture(directory, lua=False):
    empty=directory/'empty.w3x'
    ht=encrypt(struct.pack('<IIHHI',0xffffffff,0xffffffff,0xffff,0xffff,0xffffffff)*32,hash_string('(hash table)',3))
    body=b'MPQ\x1a'+struct.pack('<IIHHIIII',32,32+len(ht),0,3,32,32+len(ht),32,0)+ht
    empty.write_bytes(build_header('Synthetic pipeline fixture',0,1)+body)
    files={'war3map.j':SCRIPT.encode(),'test-asset.txt':b'preserve this asset'}
    if lua: files['war3map.lua']=b'function main() end'
    src=directory/'synthetic.w3x'
    write_files(str(empty),str(src),files)
    return src

class PipelineTests(unittest.TestCase):
    def run_pipeline(self, src, out):
        env=dict(os.environ,PYTHONIOENCODING='utf-8')
        return subprocess.run([sys.executable,str(Path(__file__).with_name('pipeline.py')),str(src),str(out)],
                              capture_output=True,text=True,encoding='utf-8',env=env)

    def test_complete_pipeline_preserves_input_runtime_and_assets(self):
        with tempfile.TemporaryDirectory(prefix='maptoolkit-test-') as directory:
            d=Path(directory); src=fixture(d); before=src.read_bytes(); out=d/'study'
            result=self.run_pipeline(src,out)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(src.read_bytes(),before)
            for name in ['1-deprotected.w3x','2-split.w3x','3-formatted.w3x']:
                m=MPQ(str(out/name))
                self.assertEqual(m.read('war3map.j'),SCRIPT.encode())
                self.assertEqual(m.read('test-asset.txt'),b'preserve this asset')
            for name in ['src/map-header.j','src/trigger-list.json','docs/TRIGGER_INDEX.md',
                         'docs/GLOBALS.md','docs/DEAD_CODE.md','compatibility.md','split-report.json','manifest.json']:
                self.assertTrue((out/name).is_file(),name)
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertEqual(manifest['input_sha256'],hashlib.sha256(before).hexdigest())
            self.assertIn('### 1.29.2: compiles',(out/'compatibility.md').read_text())

    def test_existing_study_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory); src=fixture(d); out=d/'study'; out.mkdir(); marker=out/'notes.txt'; marker.write_text('keep')
            result=self.run_pipeline(src,out)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('must be empty',result.stderr)
            self.assertEqual(marker.read_text(),'keep')

    def test_lua_is_rejected_without_mutating_input(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory); src=fixture(d,lua=True); before=src.read_bytes()
            result=self.run_pipeline(src,d/'study')
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Lua map',result.stdout)
            self.assertEqual(src.read_bytes(),before)

    def test_generated_rename_preserves_comments_and_strings(self):
        original=SCRIPT+'// main InitCustomTriggers\n'
        original=original.replace('call SetPlayers(1)','call BJDebugMsg("main InitCustomTriggers")\ncall SetPlayers(1)')
        renamed,_=rename_generated(original)
        self.assertIn('// main InitCustomTriggers',renamed)
        self.assertIn('"main InitCustomTriggers"',renamed)
        self.assertIn('function main_old ',renamed)

if __name__=='__main__': unittest.main(verbosity=2)
