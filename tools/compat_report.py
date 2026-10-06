"""Which game versions can run this map? A report on its script and file formats.

    python tools/compat_report.py MAP.w3x [--versions 1.29.2 1.31.1 3.0]

1. Script: compiles war3map.j against common.j/blizzard.j of each version (made by
   tools/version_libs.py from the annotated jassdoc libraries) and lists the natives and constants
   that version lacks. Each one is marked "editor" when it sits in code World Editor writes by
   itself (main, config, CreateAllUnits ...) - an older editor writes its own version of that
   code - or "map code" when the map's own triggers use it.
2. Files: the format version of each world/object file, with the newest version each game
   understands (Reforged-only formats must be converted for older games).
"""
import argparse, os, re, struct, subprocess, sys, tempfile
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import MPQ
from check_editable import find_tool

EDITOR_FUNCS = re.compile(r'^(main|config|InitGlobals|InitSounds|CreateRegions|CreateCameras|CreateAllUnits|CreateAllItems|'
                          r'CreateAllDestructables|CreateUnitsForPlayer\d+|CreateBuildingsForPlayer\d+|CreateNeutral\w*|'
                          r'CreatePlayerBuildings|CreatePlayerUnits|InitCustomTriggers|RunInitializationTriggers|'
                          r'InitCustomPlayerSlots|InitCustomTeams|InitAllyPriorities|InitTechTree\w*|InitUpgrades\w*|'
                          r'ItemTable\d+_DropItems|Unit\d+_DropItems|InitRandomGroups)$')

# file -> (how to read its version, {game: newest version it reads})
FORMATS = {
    'war3map.w3i': ('int0', {'1.29': 28, '1.31': 31, 'Reforged': 'any'}),
    'war3map.w3e': ('int4', {'1.29': 11, '1.31': 11, 'Reforged': 'any'}),
    'war3map.doo': ('int4', {'1.29': 8, '1.31': 8, 'Reforged': 'any'}),
    'war3mapUnits.doo': ('int4', {'1.29': 8, '1.31': 8, 'Reforged': 'any'}),
    'war3map.w3r': ('int0', {'1.29': 5, '1.31': 5, 'Reforged': 'any'}),
    'war3map.w3c': ('int0', {'1.29': 0, '1.31': 0, 'Reforged': 'any'}),
    'war3map.w3s': ('int0', {'1.29': 1, '1.31': 1, 'Reforged': 'any'}),
    'war3map.wtg': ('wtg', {'1.29': 7, '1.31': 7, 'Reforged': 'any'}),
    'war3map.wct': ('int0', {'1.29': 1, '1.31': 1, 'Reforged': 'any'}),
}
for ext in 'uatbdhq':
    FORMATS['war3map.w3' + ext] = ('int0', {'1.29': 2, '1.31': 2, 'Reforged': 'any'})

def file_version(data, how):
    if how == 'int0':
        v, = struct.unpack_from('<I', data, 0)
    elif how == 'int4':
        v, = struct.unpack_from('<I', data, 4)
    else:
        v, = struct.unpack_from('<I', data, 4)
        if v == 0x80000004:
            return 'Reforged'
    return 'Reforged' if v == 0x80000004 else v

def missing(script, common, blizzard):
    with tempfile.NamedTemporaryFile('w', suffix='.j', delete=False, encoding='utf-8') as f:
        f.write(script); path = f.name
    try:
        r = subprocess.run([find_tool('pjass', None), common, blizzard, path], capture_output=True, text=True, errors='replace')
    finally:
        os.unlink(path)
    found = []
    for line in (r.stdout + r.stderr).splitlines():
        m = re.search(r':(\d+): Undeclared (function|variable) (\w+)', line)
        if m:
            found.append((int(m.group(1)), m.group(3)))
    return found, r.returncode == 0

def owner_lines(script):
    """line number -> enclosing function name"""
    out, cur = {}, None
    for i, line in enumerate(script.split('\n'), 1):
        m = re.match(r'\s*(?:constant\s+)?function\s+(\w+)', line)
        if m:
            cur = m.group(1)
        out[i] = cur
        if re.match(r'\s*endfunction', line):
            cur = None
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map'); ap.add_argument('--versions', nargs='+', default=['1.29.2', '1.31.1', '3.0'])
    a = ap.parse_args()
    m = MPQ(a.map)
    raw = m.read('war3map.j') or m.read('scripts\\war3map.j')
    if not raw:
        sys.exit('No JASS script found; Lua maps are not supported.')
    script = raw.decode('utf-8', 'replace').replace('\r\n', '\n')
    owners = owner_lines(script)
    print('# Compatibility report: %s\n' % os.path.basename(a.map))
    print('## Script (war3map.j)\n')
    for v in a.versions:
        d = os.path.join(HERE, 'versions', v)
        if not os.path.exists(os.path.join(d, 'common.j')):
            subprocess.run([sys.executable, os.path.join(HERE, 'version_libs.py'), v], capture_output=True)
        found, ok = missing(script, os.path.join(d, 'common.j'), os.path.join(d, 'blizzard.j'))
        groups = defaultdict(lambda: [0, set()])
        for line, name in found:
            fn = owners.get(line) or '(globals)'
            kind = 'editor' if EDITOR_FUNCS.match(fn) else 'map code'
            groups[(kind, name)][0] += 1
            groups[(kind, name)][1].add(fn)
        own = [k for k in groups if k[0] == 'map code']
        print('### %s: %s' % (v, 'compiles' if ok else '%d missing names (%d in map code)' % (len(groups), len(own))))
        for (kind, name), (n, fns) in sorted(groups.items(), key=lambda kv: (kv[0][0] != 'map code', -kv[1][0])):
            print('- `%s` x%d (%s; in %s)' % (name, n, kind, ', '.join(sorted(fns))[:120]))
        print()
    print('## File formats\n')
    print('| File | Version | 1.29 reads | 1.31 reads |')
    print('|---|---|---|---|')
    for name, (how, games) in FORMATS.items():
        data = m.read(name)
        if not data:
            continue
        v = file_version(data, how)
        flag = lambda g: 'yes' if (v != 'Reforged' and isinstance(games[g], int) and v <= games[g]) else '**no** (needs %s)' % games[g]
        print('| %s | %s | %s | %s |' % (name, v, flag('1.29'), flag('1.31')))
    skins = [n for n in ('war3mapSkin.w3u', 'war3mapSkin.w3a', 'war3mapSkin.w3t') if m.read(n)]
    if skins:
        print('\nReforged-only files (ignored by older games): ' + ', '.join(skins))

if __name__ == '__main__':
    main()
