"""Run steps 1-3 on a protected map in one go, checking after every step.

    python tools/pipeline.py PROTECTED.w3x OUT_DIR

Produces in OUT_DIR:
  1-deprotected.w3x    the whole script as editable custom script + MainDeprotected trigger
  2-split.w3x          one custom-text trigger per original trigger (+ split-report.json)
  3-formatted.w3x      the same, indented                <- open this one in World Editor
  src/                 the code as plain files (for reading, searching, Git)
  docs/                TRIGGER_INDEX.md, GLOBALS.md, DEAD_CODE.md
  compatibility.md     which game versions the script and files work with
Stops at the first step that fails.
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def run(*args, out=None):
    print('>', ' '.join(os.path.basename(a) if i == 0 else a for i, a in enumerate(args)))
    r = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + list(args[1:]), capture_output=True, text=True)
    text = r.stdout + r.stderr
    if out:
        open(out, 'w', encoding='utf-8').write(text)
        print('  (written to %s)' % out)
    else:
        print('  ' + text.strip().replace('\n', '\n  '))
    if r.returncode != 0:
        sys.exit('stopped: %s failed' % args[0])

def main(src, out):
    os.makedirs(out, exist_ok=True)
    p = lambda n: os.path.join(out, n)
    for n in ('1-deprotected.w3x', '2-split.w3x', '3-formatted.w3x'):
        if os.path.exists(p(n)):
            sys.exit('%s already exists; use an empty folder' % p(n))
    run('deprotect.py', src, p('1-deprotected.w3x'))
    run('check_editable.py', p('1-deprotected.w3x'))
    run('split_modules.py', p('1-deprotected.w3x'), p('2-split.w3x'), '--report', p('split-report.json'))
    run('check_editable.py', p('2-split.w3x'))
    run('format_modules.py', p('2-split.w3x'), p('3-formatted.w3x'))
    run('check_editable.py', p('3-formatted.w3x'))
    run('export_sources.py', p('3-formatted.w3x'), p('src'))
    run('document.py', p('src'), p('docs'))
    run('compat_report.py', p('3-formatted.w3x'), out=p('compatibility.md'))
    print('done: open %s in World Editor (with JassHelper/vJass on), Save As, and play test.' % p('3-formatted.w3x'))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
