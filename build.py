#!/usr/bin/env python3
"""
Camera Report - build step
==========================

WHAT THIS DOES (plain English)
------------------------------
index.src.html is the file we EDIT. It contains the app written in JSX, plus a
copy of the Babel compiler so the browser can translate that JSX on the fly.
That works with zero setup, but it means every phone that opens the app
downloads a 2.9 MB compiler and re-translates the whole app on every launch.

This script does that translation ONCE, here, and writes index.html - the file
we actually DEPLOY. The output is identical in behaviour but ~9x smaller and
starts instantly, because the compiler is no longer needed at runtime.

    index.src.html   (edit this)  --[build.py]-->   index.html   (deploy this)

USAGE
-----
    python3 build.py

Requires: node (used only to run the Babel copy already bundled in
index.src.html - there is nothing to npm install, and no network access).

IMPORTANT
---------
Never hand-edit index.html: it is generated and will be overwritten. Make every
change in index.src.html and re-run this script.
"""

import re
import subprocess
import sys
import os
import gzip

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'index.src.html')
OUT = os.path.join(HERE, 'index.html')

# Babel's own defaults for a <script type="text/babel"> tag that carries no
# data-presets attribute. Matching them exactly means the built file behaves
# identically to the source file - notably 'env', which downlevels modern
# syntax so the app keeps working on older iPads on set.
PRESETS = ['react', 'env']
PLUGINS = ['transform-class-properties', 'transform-object-rest-spread']


def die(msg):
    print('BUILD FAILED: ' + msg, file=sys.stderr)
    sys.exit(1)


def main():
    if not os.path.exists(SRC):
        die('index.src.html not found - that is the file you edit.')

    html = open(SRC, encoding='utf-8').read()

    # 1. Locate the bundled Babel compiler (identified by its banner comment).
    babel = re.search(
        r'<script>\s*/\* @babel/standalone.*?</script>', html, re.S)
    if not babel:
        die('could not find the bundled @babel/standalone <script> block.')
    babel_js = re.sub(r'^<script>|</script>$', '', babel.group(0)).strip()

    # 2. Locate the app source (the JSX).
    app = re.search(r'<script type="text/babel">(.*?)</script>', html, re.S)
    if not app:
        die('could not find the <script type="text/babel"> app block.')
    jsx = app.group(1)

    # 3. Compile, using the very Babel copy bundled in the source file - so the
    #    build can never drift from what the browser would have done, and needs
    #    no npm install.
    tmp_babel = '/tmp/_cr_babel.js'
    tmp_jsx = '/tmp/_cr_app.jsx'
    tmp_out = '/tmp/_cr_app.js'
    open(tmp_babel, 'w', encoding='utf-8').write(babel_js)
    open(tmp_jsx, 'w', encoding='utf-8').write(jsx)

    node_script = f'''
      const fs = require('fs');
      const Babel = require({tmp_babel!r});
      const src = fs.readFileSync({tmp_jsx!r}, 'utf8');
      const out = Babel.transform(src, {{
        presets: {PRESETS!r},
        plugins: {PLUGINS!r},
        sourceMaps: false,
        compact: false
      }}).code;
      fs.writeFileSync({tmp_out!r}, out);
      console.log(out.length);
    '''
    r = subprocess.run(['node', '-e', node_script],
                       capture_output=True, text=True)
    if r.returncode != 0:
        die('Babel could not compile the app:\n' + (r.stderr or r.stdout))
    compiled = open(tmp_out, encoding='utf-8').read()

    # 4. Reassemble: drop the compiler, swap JSX for compiled JS.
    #    Order matters - splice the later block first so the earlier block's
    #    offsets stay valid.
    banner = ('/* Compiled from index.src.html by build.py - DO NOT EDIT.\n'
              '   Edit index.src.html and re-run: python3 build.py */\n')
    out_html = (html[:app.start()] + '<script>\n' + banner + compiled +
                '\n</script>' + html[app.end():])
    out_html = out_html[:babel.start()] + (
        '<!-- @babel/standalone removed: the app below is already compiled. -->'
    ) + out_html[babel.end():]

    # 5. Sanity checks before we overwrite anything.
    if 'text/babel' in out_html:
        die('output still references text/babel - the swap did not take.')
    if 'React.createElement' not in compiled:
        die('compiled output contains no React.createElement - suspicious.')
    for marker in ['CameraReport', 'camrep_projects_v1', 'ReactDOM']:
        if marker not in out_html:
            die('output is missing expected marker: ' + marker)

    open(OUT, 'w', encoding='utf-8').write(out_html)

    src_n = len(html.encode())
    out_n = len(out_html.encode())
    gz = len(gzip.compress(out_html.encode(), 9))
    print('  source  index.src.html : {:>10,} bytes'.format(src_n))
    print('  built   index.html     : {:>10,} bytes  ({:.0f}% smaller)'.format(
        out_n, (1 - out_n / src_n) * 100))
    print('  gzipped (what users get): {:>9,} bytes'.format(gz))
    print('OK')


if __name__ == '__main__':
    main()
