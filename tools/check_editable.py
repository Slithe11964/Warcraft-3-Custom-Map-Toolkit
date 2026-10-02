"""Check that a deprotected / split map will compile in World Editor, without opening it.

    python tools/check_editable.py MAP.w3x [--common common.j --blizzard blizzard.j] [--pjass PATH]

What it does:
  1. Reads the Trigger Editor text (map custom script + every custom-text trigger).
  2. Builds what World Editor + JassHelper would produce: libraries flattened in JassHelper
     order, plus the editor's own generated code for the MainDeprotected trigger and main.
  3. Compiles that with pjass against common.j/blizzard.j (pick the game version you target).
  4. If the map also has a war3map.j (the playable script), compiles that too.
  5. Warns about string literals over 1000 bytes (they break loading native saved games).
Exit code 0 when everything compiles.
"""
import argparse, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import MPQ
from wct_any import read_wct
from vjass_lite import flatten

EDITOR_TAIL = '''
function Trig_MainDeprotected_Actions takes nothing returns nothing
    call main_old()
endfunction
function InitTrig_MainDeprotected takes nothing returns nothing
    set gg_trg_MainDeprotected=CreateTrigger()
    call TriggerAddAction(gg_trg_MainDeprotected,function Trig_MainDeprotected_Actions)
endfunction
function InitCustomTriggers takes nothing returns nothing
    call InitTrig_MainDeprotected()
%s
endfunction
function RunInitializationTriggers takes nothing returns nothing
    call ConditionalTriggerExecute(gg_trg_MainDeprotected)
endfunction
function main takes nothing returns nothing
    call InitBlizzard()
    call InitCustomTriggers()
    call RunInitializationTriggers()
endfunction
function config takes nothing returns nothing
endfunction
'''

def find_tool(name, explicit):
    if explicit:
        return explicit
    for d in (os.path.join(HERE, 'bin'), HERE):
        for c in (name + '.exe', name):
            p = os.path.join(d, c)
            if os.path.exists(p):
                return p
    return name

def pjass(pj, common, blizzard, text):
    with tempfile.NamedTemporaryFile('w', suffix='.j', delete=False, encoding='utf-8') as f:
        f.write(text); path = f.name
    try:
        r = subprocess.run([pj, common, blizzard, path], capture_output=True, text=True, errors='replace')
    finally:
        os.unlink(path)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.strip() and 'Parse successful' not in l]
    return r.returncode == 0, lines

def long_strings(text, limit=1000):
    return [len(m.group(0)) for m in re.finditer(r'"(?:\\.|[^"\\])*"', text) if len(m.group(0)) > limit]

def editor_script(m):
    w = read_wct(m.read('war3map.wct'))
    texts = [e for e in w['entries'] if e.strip()]
    inits, extra = [], 'trigger gg_trg_MainDeprotected=null\n'
    for t in texts:
        # World Editor declares gg_trg_<Name> and calls InitTrig_<Name> for every trigger
        for n in re.findall(r'^\s*function\s+InitTrig_(\w+)\s+takes', t, re.M):
            inits.append('    call InitTrig_%s()' % n)
            extra += 'trigger gg_trg_%s=null\n' % n
    return flatten(w['header'], texts, extra_globals=extra, tail=EDITOR_TAIL % '\n'.join(inits), lenient=True)[0], w, len(texts)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('--common'); ap.add_argument('--blizzard'); ap.add_argument('--pjass')
    a = ap.parse_args()
    common = a.common or os.path.join(HERE, 'bin', 'common.j')
    blizzard = a.blizzard or os.path.join(HERE, 'bin', 'blizzard.j')
    pj = find_tool('pjass', a.pjass)
    m = MPQ(a.map)
    ok_all = True
    src, w, n = editor_script(m)
    ok, errs = pjass(pj, common, blizzard, src)
    print('%s editor source compiles (%s format, header + %d custom-text triggers)' % ('PASS' if ok else 'FAIL', w['format'], n))
    for e in errs[:20]:
        print('     ', e)
    ok_all &= ok
    if 'main_old' not in src:
        print('NOTE no main_old: this map does not use the MainDeprotected start-up')
    playable = m.read('war3map.j') or m.read('scripts\\war3map.j')
    if playable:
        text = playable.decode('utf-8', 'replace')
        ok, errs = pjass(pj, common, blizzard, text)
        print('%s playable script (war3map.j) compiles' % ('PASS' if ok else 'FAIL'))
        for e in errs[:20]:
            print('     ', e)
        ok_all &= ok
        big = long_strings(text)
        print('%s native save/load text safety (%d string literals over 1000 bytes%s)' %
              ('PASS' if not big else 'WARN', len(big), ', longest %d' % max(big) if big else ''))
    sys.exit(0 if ok_all else 1)

if __name__ == '__main__':
    main()
