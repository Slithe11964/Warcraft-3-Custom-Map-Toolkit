"""Export a map's Trigger Editor text to plain files, so it can be read, searched and kept in Git.

    python tools/export_sources.py MAP.w3x SRC_DIR

Writes:
  SRC_DIR/map-header.j            the map custom script
  SRC_DIR/triggers/<Name>.j       one file per custom-text trigger (named after its InitTrig_<Name>)
  SRC_DIR/trigger-list.json       the editor order (used by tools/document.py)
Works with classic (1.29-era) and Reforged maps.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import MPQ
from wct_any import read_wct

def main(map_path, src):
    w = read_wct(MPQ(map_path).read('war3map.wct'))
    os.makedirs(os.path.join(src, 'triggers', 'Modules'), exist_ok=True)
    open(os.path.join(src, 'map-header.j'), 'w', encoding='utf-8', newline='').write(w['header'])
    entries = []
    for i, text in enumerate(w['entries']):
        if not text.strip():
            entries.append(dict(index=i, name='gui-entry-%d' % i, folder='', library=None,
                                note='GUI trigger (no custom text); edit it in World Editor'))
            continue
        m = re.search(r'^\s*function\s+InitTrig_(\w+)\s+takes', text, re.M)
        name = m.group(1) if m else 'trigger-%d' % i
        lib = re.search(r'^\s*library\s+(\w+)', text, re.M)
        open(os.path.join(src, 'triggers', 'Modules', name + '.j'), 'w', encoding='utf-8', newline='').write(text)
        entries.append(dict(index=i, name=name, folder='Modules', library=lib.group(1) if lib else None))
    json.dump(entries, open(os.path.join(src, 'trigger-list.json'), 'w', encoding='utf-8'), indent=1)
    print('exported %d entries (%s format) to %s' % (len(entries), w['format'], src))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
