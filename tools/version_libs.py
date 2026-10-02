"""Make common.j / blizzard.j for an older game version from the annotated jassdoc libraries.

    python tools/version_libs.py 1.29.2 [--src DIR] [--out DIR]

jassdoc (github.com/lep/jassdoc) annotates every type, native, constant and Blizzard.j function
with `@patch X.Y` - the patch that added it. This keeps only what existed in the target patch,
so pjass can tell you whether a script would compile in that version:

    python tools/check_editable.py MAP.w3x --common versions/1.29.2/common.j --blizzard versions/1.29.2/blizzard.j

It is as accurate as jassdoc's annotations: natives whose behaviour changed (not their name) are not
detected, and unannotated declarations are kept.
"""
import argparse, os, re

DOC = re.compile(r'/\*\*(.*?)\*/', re.S)

def vtuple(s):
    return tuple(int(x) for x in re.findall(r'\d+', s))

def units(text):
    """Yield (doc, code) pairs: a declaration with the doc comment just before it."""
    pos, doc = 0, ''
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith('/**'):
            j = i
            while '*/' not in lines[j]:
                j += 1
            doc = '\n'.join(lines[i:j + 1])
            i = j + 1
            continue
        if re.match(r'\s*(constant\s+)?function\b', line):
            j = i
            while not re.match(r'\s*endfunction\b', lines[j]):
                j += 1
            yield doc, '\n'.join(lines[i:j + 1]); doc = ''; i = j + 1
            continue
        yield (doc if line.strip() else ''), line
        if line.strip():
            doc = ''
        i += 1

def patch_of(doc):
    m = re.search(r'@patch\s+([\d.]+)', doc)
    return vtuple(m.group(1)) if m else None

def filter_lib(text, target):
    out, dropped = [], []
    for doc, code in units(text.replace('\r\n', '\n')):
        p = patch_of(doc)
        if p is not None and p > target:
            dropped.append((code.split('\n')[0].strip()[:80], '.'.join(map(str, p))))
            continue
        out.append(code)
    return '\n'.join(out) + '\n', dropped

DEFAULTS = {'integer': '0', 'real': '0.', 'boolean': 'false', 'string': '""', 'code': 'null'}

def stub_functions(text):
    """Keep every Blizzard.j function's signature but give it an empty body. Some 1.29 functions
    were rewritten later to use newer natives; for checking map scripts only the signature matters."""
    return re.sub(r'^(constant\s+)?function\s+(\w+)\s+takes\s+(?P<a>.*?)\s+returns\s+(\w+)[^\n]*\n.*?^endfunction',
                  stub_m, text, flags=re.M | re.S)

def stub_m(m):
    ret = m.group(4)
    body = '' if ret == 'nothing' else '    return %s\n' % DEFAULTS.get(ret, 'null')
    return '%sfunction %s takes %s returns %s\n%sendfunction' % (m.group(1) or '', m.group(2), m.group('a'), ret, body)

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('version')
    ap.add_argument('--src', default=os.path.join(here, 'jassdoc'))
    ap.add_argument('--out')
    a = ap.parse_args()
    target = vtuple(a.version)
    target = target + (99999,) * (4 - len(target))  # "1.29.2" includes every 1.29.2.x build
    out = a.out or os.path.join(here, 'versions', a.version)
    os.makedirs(out, exist_ok=True)
    report = []
    for name, outname in (('common.j', 'common.j'), ('Blizzard.j', 'blizzard.j')):
        text = open(os.path.join(a.src, name), encoding='utf-8').read()
        kept, dropped = filter_lib(text, target)
        if name == 'Blizzard.j':
            kept = stub_functions(kept)
            # globals whose starting value calls a function are declared without it
            kept = re.sub(r'^(\s*(?!constant)\w+\s+(?:array\s+)?\w+)\s*=\s*\w+\s*\(.*$', r'\1', kept, flags=re.M)
        open(os.path.join(out, outname), 'w', encoding='utf-8').write(kept)
        report.append('%s: %d declarations newer than %s removed' % (name, len(dropped), a.version))
        with open(os.path.join(out, outname + '.removed.txt'), 'w', encoding='utf-8') as f:
            for line, p in dropped:
                f.write('%-10s %s\n' % (p, line))
    print('\n'.join(report))
    print('written to', out)

if __name__ == '__main__':
    main()
