"""Read/write war3map.wct (Trigger Editor custom text) in both formats:
  classic  (version 1; 1.07 - 1.30 editors, also opened by Reforged)
  Reforged (sub-version 0x80000004, format 1)
read_wct returns dict(format, comment, header, entries) with text strings ('' for GUI triggers).
"""
import struct

REFORGED = 0x80000004

def _text(raw):
    raw = raw[:-1] if raw.endswith(b'\0') else raw
    return raw.decode('utf-8', errors='replace')

def _raw(text):
    return (text.encode('utf-8') + b'\0') if text else b''

def read_wct(d):
    first, = struct.unpack_from('<I', d, 0)
    if first == REFORGED:
        fmt, = struct.unpack_from('<I', d, 4)
        o = 8
        e = d.index(b'\0', o); comment = d[o:e].decode('utf-8', 'replace'); o = e + 1
        n, = struct.unpack_from('<I', d, o); o += 4; header = _text(d[o:o + n]); o += n
        entries = []
        while o < len(d):
            L, = struct.unpack_from('<I', d, o); o += 4; entries.append(_text(d[o:o + L])); o += L
        return dict(format='reforged', comment=comment, header=header, entries=entries)
    if first == 1:
        o = 4
        e = d.index(b'\0', o); comment = d[o:e].decode('utf-8', 'replace'); o = e + 1
        n, = struct.unpack_from('<i', d, o); o += 4; header = _text(d[o:o + n]); o += n
        count, = struct.unpack_from('<i', d, o); o += 4
        entries = []
        for _ in range(count):
            L, = struct.unpack_from('<i', d, o); o += 4; entries.append(_text(d[o:o + L])); o += L
        return dict(format='classic', comment=comment, header=header, entries=entries)
    if first == 0:
        count, = struct.unpack_from('<i', d, 4); o = 8
        entries = []
        for _ in range(count):
            L, = struct.unpack_from('<i', d, o); o += 4; entries.append(_text(d[o:o + L])); o += L
        return dict(format='classic0', comment='', header='', entries=entries)
    raise ValueError('unknown war3map.wct format %#x' % first)

def write_wct(w):
    if w['format'] == 'reforged':
        out = struct.pack('<II', REFORGED, 1) + w['comment'].encode('utf-8') + b'\0'
        h = _raw(w['header'])
        out += struct.pack('<I', len(h)) + h
        for e in w['entries']:
            r = _raw(e); out += struct.pack('<I', len(r)) + r
        return out
    h = w['header'].encode('utf-8') + b'\0'
    out = struct.pack('<i', 1) + w['comment'].encode('utf-8') + b'\0' + struct.pack('<i', len(h)) + h
    out += struct.pack('<i', len(w['entries']))
    for e in w['entries']:
        r = _raw(e); out += struct.pack('<i', len(r)) + r
    return out
