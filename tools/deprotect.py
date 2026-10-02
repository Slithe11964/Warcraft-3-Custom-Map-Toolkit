"""Step 1: turn a protected Warcraft III map (JASS) into one World Editor can open and edit.

    python tools/deprotect.py PROTECTED.w3x OUT.w3x [--keep-world-objects]

A "protected" map ships only the compiled script (war3map.j). Its Trigger Editor data
(war3map.wtg / war3map.wct) is empty or missing, so World Editor shows nothing, or refuses to save.
This tool puts the compiled script back in as editable text:

* The whole original script becomes the map's custom script (Trigger Editor > map name entry).
* The functions World Editor writes by itself (main, config, CreateAllUnits, InitCustomTriggers ...)
  are renamed with an `_old` suffix, so the editor's own copies don't clash with them.
* One GUI trigger, MainDeprotected, runs at map initialization and calls `main_old()`.
  The original start-up then runs just as it did before.
* `call InitBlizzard()` is removed from main_old, because the editor's main already calls it.

Pre-placed units, regions, cameras and sounds:
  In a protected map the script itself creates them (CreateAllUnits, CreateRegions ...). If the
  editor ALSO has them in war3mapUnits.doo / .w3r / .w3c / .w3s, it would create them a second
  time and declare their variables twice. By default those files are emptied (the script keeps
  creating everything). The editor then no longer shows them on the map, but the game is the same.
  Doodads/trees (war3map.doo) and everything else are kept.

The output keeps the original script as war3map.j, so it is directly playable. World Editor
regenerates war3map.j when you Save As; run tools/check_editable.py on that save.

Lua maps are not supported. Maps whose names were scrambled by an optimizer stay scrambled:
this restores editability, not readability. Step 2 (tools/split_modules.py) adds structure.
"""
import argparse, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import MPQ, write_files, compact

# Functions World Editor generates for every map (or for maps with preplaced objects).
WE_GENERATED = re.compile(r'^(main|config|InitGlobals|InitSounds|CreateRegions|CreateCameras|CreateAllUnits|'
                          r'CreateAllItems|CreateAllDestructables|CreateUnitsForPlayer\d+|CreateBuildingsForPlayer\d+|'
                          r'CreateNeutralHostile\w*|CreateNeutralPassive\w*|CreateNeutralUnits|CreatePlayerBuildings|'
                          r'CreatePlayerUnits|InitCustomTriggers|RunInitializationTriggers|InitCustomPlayerSlots|'
                          r'InitCustomTeams|InitAllyPriorities|InitTechTree\w*|InitUpgrades\w*|ItemTable\d+_DropItems|'
                          r'Unit\d+_DropItems|InitRandomGroups|InitMapRects|CreateAllMapItems|InitTrig_MainDeprotected|'
                          r'InitGeneratedCode|InitDNCSounds|InitCameras)$')
WORLD_OBJECT_FILES = {
    'war3mapUnits.doo': None,  # replaced by an empty units file (see EMPTY_UNITS)
    'war3map.w3r': b'\x05\x00\x00\x00\x00\x00\x00\x00',       # regions: version 5, 0 regions
    'war3map.w3c': b'\x00\x00\x00\x00\x00\x00\x00\x00',       # cameras: version 0, 0 cameras
    'war3map.w3s': b'\x01\x00\x00\x00\x00\x00\x00\x00',       # sounds: version 1, 0 sounds
}
SCRIPT_NAMES = ['war3map.j', 'scripts\\war3map.j', 'Scripts\\war3map.j']

def empty_units(orig):
    """An empty war3mapUnits.doo that keeps the original's header (format and sub-version)."""
    if orig and len(orig) >= 16 and orig[:4] == b'W3do':
        version, sub = struct.unpack_from('<Ii', orig, 4)
        if version >= 8:
            return b'W3do' + struct.pack('<IiI', version, sub, 0)
    return b'W3do' + struct.pack('<IiI', 8, 11, 0)

def wtg_classic():
    """Trigger tree, classic format 7 (opened by both 1.29-era and Reforged World Editors):
    one folder "Triggers" with the GUI trigger MainDeprotected:
        Event: Map initialization      Action: Custom script: call main_old()"""
    def s(x): return x.encode('utf-8') + b'\0'
    def i(x): return struct.pack('<i', x)
    cat = 0x02000001
    out = b'WTG!' + i(7) + i(1) + i(cat) + s('Triggers') + i(0) + i(2) + i(0)
    out += i(1) + s('MainDeprotected') + s('Runs the original map script, kept as custom script code.')
    out += i(0) + i(1) + i(0) + i(0) + i(0) + i(cat) + i(2)
    out += i(0) + s('MapInitializationEvent') + i(1) + i(0)
    out += i(2) + s('CustomScriptCode') + i(1) + i(3) + s('call main_old()') + i(0) + i(0) + i(0)
    return out

def wct_classic(header, comment):
    raw = header.encode('utf-8') + b'\0'
    return struct.pack('<i', 1) + comment.encode('utf-8') + b'\0' + struct.pack('<i', len(raw)) + raw + struct.pack('<ii', 1, 0)

def rename_generated(script):
    names = re.findall(r'^\s*function\s+(\w+)\s+takes', script, re.M)
    renamed = sorted({n for n in names if WE_GENERATED.match(n)})
    taken = set(names)
    mapping = {}
    for n in renamed:
        new = n + '_old'
        while new in taken:
            new += '_'
        mapping[n] = new
        taken.add(new)
    if mapping:
        pat = re.compile(r'\b(%s)\b' % '|'.join(map(re.escape, sorted(mapping, key=len, reverse=True))))
        # rename identifiers outside of string literals and comments
        out, pos = [], 0
        for m in re.finditer(r'"(?:\\.|[^"\\])*"|//[^\n]*', script):
            out.append(pat.sub(lambda x: mapping[x.group(1)], script[pos:m.start()]))
            out.append(m.group(0))
            pos = m.end()
        out.append(pat.sub(lambda x: mapping[x.group(1)], script[pos:]))
        script = ''.join(out)
    return script, mapping

def strip_initblizzard(script):
    m = re.search(r'^function main_old takes nothing returns nothing\n(.*?)^endfunction', script, re.M | re.S)
    if not m:
        return script, 0
    body, n = re.subn(r"^[ \t]*call\s+InitBlizzard\s*\(\s*\)[ \t]*\n", "", m.group(1), flags=re.M)
    return script[:m.start(1)] + body + script[m.end(1):], n

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map'); ap.add_argument('out')
    ap.add_argument('--keep-world-objects', action='store_true',
                    help="don't empty war3mapUnits.doo/.w3r/.w3c/.w3s (only for maps whose script does NOT create them)")
    a = ap.parse_args()
    m = MPQ(a.map)
    if m.read('war3map.lua') is not None:
        sys.exit('this is a Lua map; only JASS maps are supported')
    script_name = next((n for n in SCRIPT_NAMES if m.read(n)), None)
    if script_name is None:
        sys.exit('no war3map.j found in the map')
    raw = m.read(script_name)
    script = raw.decode('utf-8', errors='surrogateescape').replace('\r\n', '\n')
    wct = m.read('war3map.wct')
    if wct and len(wct) > 64:
        print('note: this map already has Trigger Editor text (%d bytes); it may not be protected' % len(wct))
    script, mapping = rename_generated(script)
    if 'main' not in mapping:
        sys.exit('no main function found: is this really a war3map.j?')
    script, removed = strip_initblizzard(script)
    header = script.replace('\n', '\r\n')
    files = {
        'war3map.wtg': wtg_classic(),
        'war3map.wct': wct_classic(header.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace'),
                                   'Original war3map.j of the protected map. The functions the World Editor '
                                   'generates by itself were renamed with the _old suffix.'),
        'war3map.j': raw,
    }
    for n in SCRIPT_NAMES[1:]:
        if m.read(n) is not None:
            files[n] = None
    emptied = []
    if not a.keep_world_objects:
        for name, empty in WORLD_OBJECT_FILES.items():
            old = m.read(name)
            if old:
                files[name] = empty_units(old) if name == 'war3mapUnits.doo' else empty
                emptied.append(name)
    tmp = a.out + '.tmp'
    write_files(a.map, tmp, files)
    compact(tmp, a.out)
    os.remove(tmp)
    print('deprotected %s -> %s' % (os.path.basename(a.map), a.out))
    print('  script: %s, %d functions, %d bytes' % (script_name, len(re.findall(r'^function ', script, re.M)), len(raw)))
    print('  renamed (editor-generated): %s' % ', '.join('%s->%s' % kv for kv in sorted(mapping.items())))
    print('  InitBlizzard calls removed from main_old: %d' % removed)
    if emptied:
        print('  emptied (the script creates these itself): %s' % ', '.join(emptied))
    print('Next: python tools/check_editable.py %s, then open it in World Editor.' % a.out)

if __name__ == '__main__':
    main()
