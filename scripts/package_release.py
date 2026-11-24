#!/usr/bin/env python3
# Run me when: I need to build the versioned static and offline release files.
"""Build the release from an explicit list of source files.

The build is deterministic. The same sources give the same bytes. The
output goes outside the repository. The release is one classic script
layout, so it runs from a local file with no server and no network:

    index.html, style.<hash>.css, deck.<hash>.js, wordlist.<hash>.js

It also builds one self-contained file, passphrase.html. The file holds the
stylesheet in one <style> element. It holds the wordlist and the deck script
in one inline <script>. A meta CSP allows each block by its SHA-256 hash.

Usage: python3 scripts/package_release.py --out DIR [--version X.Y.Z]
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_wordlist  # noqa: E402

VERSION = '1.0.0'
NAME = 'passphrase-deck'
# The explicit list of application sources. Nothing else is packaged.
SOURCES = {
    'index': 'web/index.html',
    'style': 'web/style.css',
    'core': 'web/core.js',
    'app': 'web/app.js',
    'wordlist': 'data/eff_large_wordlist.txt',
}
ZIP_TIME = (1980, 1, 1, 0, 0, 0)

OFFLINE_USAGE = """Passphrase Deck offline copy

1. Unpack the zip file to a folder on your device.
2. Open passphrase.html in a web browser. You need no server and no network.
3. The file is the whole app. The page makes one passphrase in two
   formats. It never sends data.
4. If Copy fails, the browser blocked clipboard access for local files.
   Press Reveal, select the text, and copy it by hand.
5. Check the file first. Compare its SHA-256 sum with SHA256SUMS from
   the release. Use: python3 scripts/verify_release.py --check-folder DIR
   --manifest release-manifest.json

The page runs the code in this file. Keep the file read-only.
Word list: EFF long list, CC BY 4.0, https://www.eff.org/dice
"""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'expected one match for: {old[:40]}')
    return text.replace(old, new)


def classic_script(core, app):
    """Join the two modules into one classic script inside a closure."""
    core = re.sub(r'^export ', '', core, flags=re.MULTILINE)
    # The one import statement may span several lines.
    match = re.match(r"import\s*\{[^}]*\}\s*from\s*'\./core\.js';[ \t]*\n", app)
    if not match or 'export ' in app[match.end():]:
        raise ValueError('unexpected app.js module layout')
    rest = app[match.end():]
    if re.search(r'^import ', core + rest, flags=re.MULTILINE):
        raise ValueError('unexpected import statement')
    return "(function () {\n'use strict';\n" + core + '\n' + rest + '\n})();\n'


def load_parts(root=ROOT):
    """Return (text, raw, script, wordlist). Raise on a wordlist mismatch."""
    raw = {key: (root / path).read_bytes() for key, path in SOURCES.items()}
    if sha256(raw['wordlist']) != verify_wordlist.SHA256:
        raise ValueError('wordlist SHA-256 mismatch')
    text = {key: value.decode('utf-8') for key, value in raw.items()}
    script = classic_script(text['core'], text['app']).encode('utf-8')
    wordlist = ('globalThis.PASSPHRASE_DECK_WORDLIST = '
                + json.dumps(text['wordlist']) + ';\n').encode('ascii')
    return text, raw, script, wordlist


def csp_hash(text):
    """Return the CSP source for one inline block. The text is exact."""
    digest = hashlib.sha256(text.encode('utf-8')).digest()
    return "'sha256-" + base64.b64encode(digest).decode('ascii') + "'"


def build_single(root=ROOT):
    """Return the bytes of passphrase.html. Raise on any mismatch."""
    text, _, script, wordlist = load_parts(root)
    style_text = '\n' + text['style'].rstrip() + '\n'
    script_text = '\n' + (wordlist + script).decode('utf-8')
    if re.search(r'<!--|</?script', script_text, flags=re.IGNORECASE):
        raise ValueError('the inline script holds markup that ends the block')
    if re.search(r'</style|<!--', style_text, flags=re.IGNORECASE):
        raise ValueError('the inline style holds markup that ends the block')
    html = text['index']
    html = _replace_once(
        html, "script-src 'self'; style-src 'self'; connect-src 'self'; ",
        f"script-src {csp_hash(script_text)}; style-src {csp_hash(style_text)}; ")
    html = _replace_once(html, '<link rel="stylesheet" href="style.css">',
                         f'<style>{style_text}</style>')
    html = _replace_once(html, '  <script type="module" src="app.js"></script>\n', '')
    # Cloudflare Rocket Loader rewrites plain inline scripts. data-cfasync keeps ours as is.
    html = _replace_once(html, '</body>', f'<script data-cfasync="false">{script_text}</script>\n</body>')
    return html.encode('utf-8')


def build_assets(root=ROOT):
    """Return {name: bytes} for the site files. Raise on any mismatch."""
    text, raw, script, wordlist = load_parts(root)
    style = raw['style']
    names = {
        'style': f'style.{sha256(style)[:12]}.css',
        'deck': f'deck.{sha256(script)[:12]}.js',
        'wordlist': f'wordlist.{sha256(wordlist)[:12]}.js',
    }
    html = text['index']
    html = _replace_once(html, '<link rel="stylesheet" href="style.css">',
                         f'<link rel="stylesheet" href="{names["style"]}">')
    html = _replace_once(
        html, '<script type="module" src="app.js"></script>',
        f'<script defer src="{names["wordlist"]}"></script>\n'
        f'  <script defer src="{names["deck"]}"></script>')
    html = _replace_once(html, "connect-src 'self'; ", '')
    return {
        'index.html': html.encode('utf-8'),
        names['style']: style,
        names['deck']: script,
        names['wordlist']: wordlist,
    }


def make_zip(path, entries):
    """Write a zip with fixed times, order and modes. It is reproducible."""
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, entries[name])


def build(out, version=VERSION, root=ROOT):
    """Build the release in the folder out. Return the manifest."""
    out = Path(out).resolve()
    if out == root or root in out.parents:
        raise ValueError('output must be outside the repository')
    out.mkdir(parents=True, exist_ok=True)
    assets = build_assets(root)
    site = out / 'site'
    site.mkdir(exist_ok=True)
    for name, data in assets.items():
        (site / name).write_bytes(data)
    prefix = f'{NAME}-{version}'
    single = build_single(root)
    (out / 'passphrase.html').write_bytes(single)
    # The offline zip holds the one file. The static zip keeps the site files.
    offline = {f'{prefix}/passphrase.html': single}
    offline[f'{prefix}/OFFLINE-USAGE.txt'] = OFFLINE_USAGE.encode('utf-8')
    zips = {f'{prefix}-static.zip': assets, f'{prefix}-offline.zip': offline}
    for zip_name, entries in zips.items():
        make_zip(out / zip_name, entries)
    manifest = {
        'name': NAME,
        'version': version,
        'assets': {name: sha256(data) for name, data in sorted(assets.items())},
        'single_file': {'passphrase.html': sha256(single)},
        'artifacts': {name: sha256((out / name).read_bytes()) for name in sorted(zips)},
        'wordlist_sha256': verify_wordlist.SHA256,
    }
    (out / 'release-manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    sums = [f'{digest}  {name}' for name, digest in manifest['artifacts'].items()]
    sums += [f'{digest}  site/{name}' for name, digest in manifest['assets'].items()]
    sums += [f'{digest}  {name}' for name, digest in manifest['single_file'].items()]
    sums.append(f'{sha256((out / "release-manifest.json").read_bytes())}  release-manifest.json')
    (out / 'SHA256SUMS').write_text('\n'.join(sums) + '\n', encoding='utf-8')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', required=True, help='output folder outside the repository')
    parser.add_argument('--version', default=VERSION)
    args = parser.parse_args(argv)
    try:
        manifest = build(args.out, args.version)
    except (OSError, ValueError) as error:
        print(f'package_release: {error}', file=sys.stderr)
        return 1
    print(f'Built {NAME} {manifest["version"]} in {Path(args.out).resolve()}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
