"""Step 3b: indent every function of a map's Trigger Editor text (formatting only).

    python tools/format_modules.py MAP.w3x OUT.w3x

Protected and optimized maps usually have no indentation at all. This re-indents every function
(body one level in, nested if/loop blocks deeper) and removes blank lines inside functions.
It checks that the code tokens of every function are unchanged before writing.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import MPQ, write_files, compact
from wct_any import read_wct, write_wct
from jfmt import reindent_function
from jtok import tokens

FUNC = re.compile(r'^[ \t]*(?:constant[ \t]+)?function[ \t]+\w+[ \t]+takes\b.*?^[ \t]*endfunction[^\n]*', re.M | re.S)

def fmt(text):
    text = text.replace('\r\n', '\n')
    out = FUNC.sub(lambda m: reindent_function(m.group(0)), text)
    if tokens(out) != tokens(text):
        raise RuntimeError('formatting changed code tokens')
    return out.replace('\n', '\r\n')

def main(src, dst):
    m = MPQ(src)
    w = read_wct(m.read('war3map.wct'))
    w['header'] = fmt(w['header'])
    w['entries'] = [fmt(e) if e.strip() else e for e in w['entries']]
    tmp = dst + '.tmp'
    write_files(src, tmp, {'war3map.wct': write_wct(w)})
    compact(tmp, dst); os.remove(tmp)
    print('formatted the map custom script and %d custom-text triggers' % sum(1 for e in w['entries'] if e.strip()))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
