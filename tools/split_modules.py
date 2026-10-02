"""Step 2: split the one big custom script of a deprotected map into one Trigger Editor entry per
trigger (a "module"), the way the original author's triggers were organised.

    python tools/split_modules.py DEPROTECTED.w3x OUT.w3x [--report report.json]

How functions are assigned:
* Every trigger the original map created (InitCustomTriggers_old calls InitTrig_<Name>) becomes a
  module <Name>. Its roots are InitTrig_<Name> and the functions named Trig_<Name>_...
* A helper function belongs to the module whose code calls it. A helper that several modules call
  goes into the "Shared" module.
* Modules become vJass libraries (`library T<Name> requires TShared ...`); JassHelper then orders
  them so every function is defined before it is used. Modules that call each other in a circle
  are merged into one module.
* The start-up code (main_old and the other *_old functions) and anything only they use stay in
  the map custom script, which runs after all libraries.
* All variables stay in the map custom script for now (moving them is a later, map-specific step).
* InitTrig_<Name> becomes Register_<Name>; main_old still calls it at the same moment, so the start-up
  order is unchanged. Each module gets an empty InitTrig_<Name>, which World Editor requires.
* World Editor declares gg_trg_<Name> for every trigger in the tree, so those declarations are
  removed from the custom script.

Function bodies are not changed (apart from those renames). Run tools/check_editable.py on the result.
"""
import argparse, json, os, re, struct, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import MPQ, write_files, compact
from wct_any import read_wct, write_wct

FUNC_RE = re.compile(r'^[ \t]*(?:constant[ \t]+)?function[ \t]+(\w+)[ \t]+takes\b.*?^[ \t]*endfunction[^\n]*\n?', re.M | re.S)
GLOBALS_RE = re.compile(r'^[ \t]*globals[ \t]*\n(.*?)^[ \t]*endglobals[^\n]*\n?', re.M | re.S)
STRING_OR_COMMENT = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*')

def code_tokens(text):
    """Identifiers used in code (strings and comments removed) plus ExecuteFunc("Name") targets."""
    names = set(re.findall(r'ExecuteFunc\s*\(\s*"(\w+)"', text))
    names |= set(re.findall(r'\b[A-Za-z_]\w*\b', STRING_OR_COMMENT.sub(' ', text)))
    return names

def parse(header):
    header = header.replace('\r\n', '\n')
    gm = GLOBALS_RE.search(header)
    funcs = []
    pos = gm.end() if gm else 0
    for m in FUNC_RE.finditer(header, pos):
        lead = header[pos:m.start()]
        funcs.append(dict(name=m.group(1), text=lead + m.group(0)))
        pos = m.end()
    tail = header[pos:]
    return header[:gm.start()] if gm else '', gm.group(1) if gm else '', funcs, tail

def sccs(nodes, edges):
    index, low, stack, on, out, n = {}, {}, [], set(), [], [0]
    sys.setrecursionlimit(100000)
    def visit(v):
        index[v] = low[v] = n[0]; n[0] += 1; stack.append(v); on.add(v)
        for w in edges.get(v, ()):
            if w not in index:
                visit(w); low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); on.discard(w); comp.append(w)
                if w == v:
                    break
            out.append(comp)
    for v in nodes:
        if v not in index:
            visit(v)
    return out

def wtg_classic(modules):
    """Trigger tree, classic format 7: folder "Map start" with MainDeprotected, folder "Modules"
    with one custom-text trigger per module."""
    def s(x): return x.encode('utf-8') + b'\0'
    def i(x): return struct.pack('<i', x)
    start, mods = 0x02000001, 0x02000002
    out = b'WTG!' + i(7) + i(2) + i(start) + s('Map start') + i(0) + i(mods) + s('Modules') + i(0) + i(2) + i(0)
    out += i(1 + len(modules))
    out += s('MainDeprotected') + s('Runs the original map start-up (main_old in the map custom script).')
    out += i(0) + i(1) + i(0) + i(0) + i(0) + i(start) + i(2)
    out += i(0) + s('MapInitializationEvent') + i(1) + i(0)
    out += i(2) + s('CustomScriptCode') + i(1) + i(3) + s('call main_old()') + i(0) + i(0) + i(0)
    for name in modules:
        out += s(name) + s('') + i(0) + i(1) + i(1) + i(0) + i(0) + i(mods) + i(0)
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map'); ap.add_argument('out'); ap.add_argument('--report')
    a = ap.parse_args()
    m = MPQ(a.map)
    w = read_wct(m.read('war3map.wct'))
    if any(e.strip() for e in w['entries']):
        sys.exit('this map already has custom-text triggers; split_modules expects the output of deprotect.py')
    pre, globals_text, funcs, tail = parse(w['header'])
    by_name = {f['name']: f for f in funcs}
    order = [f['name'] for f in funcs]
    if 'main_old' not in by_name:
        sys.exit('no main_old: run deprotect.py first')
    init = by_name.get('InitCustomTriggers_old', {}).get('text', '') + by_name['main_old']['text']
    triggers = []
    for t in re.findall(r'\bcall\s+InitTrig_(\w+)\s*\(', init):
        if t not in triggers and 'InitTrig_' + t in by_name:
            triggers.append(t)
    names = set(by_name)
    calls = {n: (code_tokens(by_name[n]['text']) & names) - {n} for n in order}
    # roots of each module
    root_of = {}
    for t in triggers:
        root_of['InitTrig_' + t] = t
    for n in order:
        mm = re.match(r'Trig_(.+?)_(?:Actions|Conditions|Func\d+\w*|\w+)$', n)
        if n not in root_of and mm:
            for t in sorted(triggers, key=len, reverse=True):
                if n.startswith('Trig_' + t + '_'):
                    root_of[n] = t
                    break
    startup = {n for n in order if n.endswith('_old')}
    reached = defaultdict(set)
    for t in triggers:
        stack = [r for r, owner in root_of.items() if owner == t]
        seen = set(stack)
        while stack:
            f = stack.pop()
            reached[f].add(t)
            for g in calls[f]:
                if g in seen or g in startup or (g in root_of and root_of[g] != t):
                    continue
                seen.add(g); stack.append(g)
    owner = {}
    for n in order:
        if n in startup:
            continue
        if n in root_of:
            owner[n] = root_of[n]
        elif len(reached[n]) == 1:
            owner[n] = next(iter(reached[n]))
        elif len(reached[n]) > 1:
            owner[n] = 'Shared'
    # functions not owned by a module but called by module code must also be in a library
    changed = True
    while changed:
        changed = False
        for n in list(owner):
            for g in calls[n]:
                if g not in owner and g not in startup:
                    owner[g] = 'Shared'; changed = True
                elif g in startup:
                    sys.exit('module function %s calls start-up function %s; cannot split this map automatically' % (n, g))
    # library graph, merge cycles
    mods = sorted(set(owner.values()))
    deps = defaultdict(set)
    for n, o in owner.items():
        for g in calls[n]:
            if g in owner and owner[g] != o:
                deps[o].add(owner[g])
    merged = {}
    for comp in sccs(mods, deps):
        target = 'Shared' if 'Shared' in comp else sorted(comp, key=lambda x: (triggers.index(x) if x in triggers else 1e9))[0]
        for c in comp:
            merged[c] = target
    owner = {n: merged[o] for n, o in owner.items()}
    deps2 = defaultdict(set)
    for n, o in owner.items():
        for g in calls[n]:
            if g in owner and owner[g] != o:
                deps2[o].add(owner[g])
    module_names = [t for t in triggers if t in set(owner.values())]
    if 'Shared' in set(owner.values()):
        module_names = ['Shared'] + module_names
    lib = lambda t: 'T' + t.replace('_', '')
    if len({lib(t) for t in module_names}) != len(module_names):
        sys.exit('two modules map to the same library name')
    # renames: InitTrig_X -> Register_X (calls in start-up code follow)
    ren = {'InitTrig_' + t: 'Register_' + t for t in triggers}
    clash = set(ren.values()) & names
    if clash:
        sys.exit('names already used: %s' % ', '.join(sorted(clash)))
    ren_re = re.compile(r'\b(%s)\b' % '|'.join(map(re.escape, ren))) if ren else None
    def apply(text):
        if not ren_re:
            return text
        out, pos = [], 0
        for mm in STRING_OR_COMMENT.finditer(text):
            out.append(ren_re.sub(lambda x: ren[x.group(1)], text[pos:mm.start()])); out.append(mm.group(0)); pos = mm.end()
        out.append(ren_re.sub(lambda x: ren[x.group(1)], text[pos:]))
        return ''.join(out)
    module_text = {}
    merged_into = defaultdict(list)
    for c, tgt in merged.items():
        if c != tgt:
            merged_into[tgt].append(c)
    for t in module_names:
        body = ''.join(apply(by_name[n]['text']) for n in order if owner.get(n) == t)
        req = sorted(lib(d) for d in deps2.get(t, ()) if d != t)
        note = ''
        if merged_into.get(t):
            note = '// Also holds the code of: %s (they call each other).\n' % ', '.join(sorted(merged_into[t]))
        desc = 'Helpers used by several triggers.' if t == 'Shared' else 'Code of the original trigger "%s".' % t
        module_text[t] = ('library %s%s\n// %s\n%s%s\nfunction InitTrig_%s takes nothing returns nothing\n'
                          '    // Empty on purpose: the original start-up (main_old) creates this trigger through\n'
                          '    // Register_%s, at the same moment as before.\nendfunction\n\nendlibrary\n') % (
            lib(t), (' requires ' + ', '.join(req)) if req else '', desc, note, body.rstrip('\n') + '\n', t, t)
    # map custom script: globals (minus editor-declared gg_trg_<Module>) + start-up code
    gtrig = {'gg_trg_' + t for t in module_names} | {'gg_trg_MainDeprotected'}
    kept, dropped = [], []
    for line in globals_text.split('\n'):
        mm = re.match(r'\s*trigger\s+(gg_trg_\w+)\s*(?:=\s*(.*))?$', line.split('//')[0])
        if mm and mm.group(1) in gtrig:
            if mm.group(2) and mm.group(2).strip() != 'null':
                sys.exit('%s has a starting value (%s); rename that module first' % (mm.group(1), mm.group(2)))
            dropped.append(mm.group(1)); continue
        kept.append(line)
    header_funcs = ''.join(apply(by_name[n]['text']) for n in order if n not in owner)
    header = pre + 'globals\n' + '\n'.join(kept) + 'endglobals\n' + header_funcs + tail
    entries = [''] + [module_text[t] for t in module_names]
    wct = dict(format='classic', comment=w['comment'] or '', header=header.replace('\n', '\r\n'),
               entries=[e.replace('\n', '\r\n') for e in entries])
    tmp = a.out + '.tmp'
    write_files(a.map, tmp, {'war3map.wct': write_wct(wct), 'war3map.wtg': wtg_classic(module_names)})
    compact(tmp, a.out); os.remove(tmp)
    counts = defaultdict(int)
    for o in owner.values():
        counts[o] += 1
    print('split %d functions: %d in %d modules, %d stay in the map custom script (start-up code)' %
          (len(order), len(owner), len(module_names), len(order) - len(owner)))
    print('  Shared module: %d functions; merged circular modules: %d' % (counts.get('Shared', 0), sum(len(v) for v in merged_into.values())))
    print('  removed %d gg_trg_ declarations World Editor now makes itself' % len(dropped))
    if a.report:
        json.dump(dict(modules={t: sorted(n for n, o in owner.items() if o == t) for t in module_names},
                       requires={lib(t): sorted(lib(d) for d in deps2.get(t, ())) for t in module_names},
                       merged={k: v for k, v in merged_into.items()},
                       startup=[n for n in order if n not in owner]), open(a.report, 'w'), indent=1)

if __name__ == '__main__':
    main()
