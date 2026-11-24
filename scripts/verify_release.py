#!/usr/bin/env python3
# Run me when: I need to verify a release build, a folder, or the production host.
"""Verify the Passphrase Deck release.

Modes:
  --self-test                       build twice and test every check
  --verify OUT                      check a build folder made by package_release.py
  --check-folder DIR --manifest F   check an unpacked folder against a manifest
  --production URL --evidence F [--manifest F]
                                    read-only check of the hosted release

The production mode only reads. It sends GET requests to the given URL.
It never prints generated values and it holds none.
"""
import argparse
from datetime import date
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import ssl
import sys
import tempfile
from urllib.parse import urlparse
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import package_release  # noqa: E402
import verify_wordlist  # noqa: E402

REVISION = re.compile(r'[0-9a-f]{40}')
DIGEST = re.compile(r'[0-9a-f]{64}')
PLATFORMS = ('iOS Safari', 'Android Chrome')
HSTS_MIN = 15552000
IMMUTABLE_MIN = 31536000
SAFE_SOURCES = {"'none'", "'self'"}
REQUIRED_CSP = {
    'default-src': "'none'", 'script-src': "'self'", 'style-src': "'self'",
    'base-uri': "'none'", 'form-action': "'none'",
}
HEADER_ONLY_CSP = {'frame-ancestors': "'none'"}
NONE_IF_PRESENT = ('connect-src', 'object-src', 'frame-src', 'child-src')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- static checks

def parse_csp(text):
    policy = {}
    for part in text.split(';'):
        tokens = part.split()
        if tokens:
            policy[tokens[0].lower()] = tokens[1:]
    return policy


HASH_SOURCE = re.compile(r"'sha256-[A-Za-z0-9+/]{43}='")


def csp_hash(text):
    return package_release.csp_hash(text)


def check_csp(text, header=False, hashes=None):
    """Check a policy. The header form also needs frame-ancestors.

    For a single file, hashes is {'script-src': [source], 'style-src': [source]}.
    The policy must then allow exactly those hash sources and no 'self'.
    """
    problems = []
    policy = parse_csp(text)
    required = {name: [value] for name, value in REQUIRED_CSP.items()}
    if hashes is not None:
        required.update({name: sorted(set(values)) for name, values in hashes.items()})
    if header:
        required.update({name: [value] for name, value in HEADER_ONLY_CSP.items()})
    for name, value in required.items():
        if sorted(policy.get(name, [])) != value or len(policy.get(name, [])) != len(value):
            problems.append(f'CSP needs {name} {" ".join(value)}')
    for name in NONE_IF_PRESENT:
        if name in policy and policy[name] != ["'none'"]:
            problems.append(f'CSP {name} must be none')
    for name, sources in policy.items():
        for source in sources:
            allowed = source in SAFE_SOURCES or (hashes is not None and HASH_SOURCE.fullmatch(source))
            if not allowed:
                problems.append(f'CSP {name} allows more than self or none: {source[:20]}')
    return problems


def is_local(url):
    """True for a relative URL with no scheme and no host."""
    return not re.match(r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)', url.strip())


class PageScan(HTMLParser):
    """Collect unsafe markup. Navigation links may point outside."""

    def __init__(self, inline=False):
        super().__init__()
        self.inline = inline
        self.problems = []
        self.csp = []
        self.refs = []
        self.blocks = {'script': [], 'style': []}
        self._script = None
        self._open = None

    def handle_data(self, data):
        if self._open is not None:
            self._open.append(data)

    def handle_starttag(self, tag, attrs):
        attrs = {name: value or '' for name, value in attrs}
        for name in attrs:
            if name.startswith('on'):
                self.problems.append(f'inline event handler {name} on <{tag}>')
        if 'style' in attrs:
            self.problems.append(f'inline style on <{tag}>')
        if tag == 'style':
            if self.inline:
                self._open = []
                self.blocks['style'].append(self._open)
            else:
                self.problems.append('inline <style> element')
        if tag in ('iframe', 'frame', 'object', 'embed', 'base'):
            self.problems.append(f'<{tag}> element')
        if tag == 'script':
            self._script = attrs.get('src')
            if self._script is None and self.inline:
                self._open = []
                self.blocks['script'].append(self._open)
            elif self._script is None:
                self.problems.append('inline <script> element')
            elif not is_local(self._script):
                self.problems.append(f'external script {self._script}')
            else:
                self.refs.append(self._script)
        if tag == 'link' and 'href' in attrs:
            if not is_local(attrs['href']):
                self.problems.append(f'external link resource {attrs["href"]}')
            else:
                self.refs.append(attrs['href'])
        if tag in ('img', 'source', 'audio', 'video', 'track') and 'src' in attrs:
            if not is_local(attrs['src']):
                self.problems.append(f'external <{tag}> src {attrs["src"]}')
            else:
                self.refs.append(attrs['src'])
        if tag == 'form' and attrs.get('action', ''):
            self.problems.append('form with an action')
        for name, value in attrs.items():
            if value.strip().lower().startswith('javascript:'):
                self.problems.append(f'javascript: URL in {name}')
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'content-security-policy':
            self.csp.append(attrs.get('content', ''))

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._open = None
        if tag == 'script':
            self._script = None

    def inline_text(self, kind):
        """Return the exact text of each inline block of one kind."""
        return [''.join(parts) for parts in self.blocks[kind]]


JS_BANNED = [
    (r'\beval\s*\(', 'eval'),
    (r'\bnew\s+Function\b', 'new Function'),
    (r'\bFunction\s*\(', 'Function constructor'),
    (r'\bdocument\.write', 'document.write'),
    (r'\binnerHTML\b|\bouterHTML\b|\binsertAdjacentHTML\b', 'HTML string sink'),
    (r'\bimportScripts\b', 'importScripts'),
    (r'\bXMLHttpRequest\b', 'XMLHttpRequest'),
    (r'\bWebSocket\b', 'WebSocket'),
    (r'\bEventSource\b', 'EventSource'),
    (r'\bsendBeacon\b', 'sendBeacon'),
    (r'\bimport\s*\(', 'dynamic import'),
    (r'\bserviceWorker\b', 'service worker'),
    (r'\bjavascript:', 'javascript: URL'),
    (r'(?:https?|wss?|ftp):\/\/', 'absolute URL in script'),
    (r'(?<![:\w])\/\/[a-z0-9.-]+\.[a-z]{2,}\/', 'protocol-relative URL in script'),
]


def check_js(name, text):
    problems = [f'{name}: {label}' for pattern, label in JS_BANNED if re.search(pattern, text)]
    for match in re.finditer(r'\bfetch\s*\(\s*([^)]*)', text):
        literal = re.match(r'''['"]([^'"]*)['"]''', match.group(1).strip())
        if not literal or not is_local(literal.group(1)):
            problems.append(f'{name}: fetch of a non-local URL')
    return problems


def check_css(name, text):
    problems = []
    if re.search(r'@import', text):
        problems.append(f'{name}: @import')
    for match in re.finditer(r'url\(\s*[\'"]?([^\'")]*)', text):
        if not is_local(match.group(1)):
            problems.append(f'{name}: external url() {match.group(1)}')
    return problems


def check_site(files):
    """Check {name: bytes}. Return a list of problems."""
    problems = []
    if 'index.html' not in files:
        return ['index.html is missing']
    scan = PageScan()
    scan.feed(files['index.html'].decode('utf-8'))
    problems += scan.problems
    if len(scan.csp) != 1:
        problems.append('index.html needs exactly one CSP meta element')
    for text in scan.csp:
        problems += [f'meta {item}' for item in check_csp(text)]
    for ref in scan.refs:
        if ref not in files:
            problems.append(f'referenced file is not packaged: {ref}')
    for name, data in sorted(files.items()):
        if name.endswith('.js'):
            problems += check_js(name, data.decode('utf-8'))
        elif name.endswith('.css'):
            problems += check_css(name, data.decode('utf-8'))
        elif not name.endswith('.html'):
            problems.append(f'unexpected file type: {name}')
    for name in files:
        if name not in scan.refs and name != 'index.html':
            problems.append(f'file is not used by index.html: {name}')
    return problems


def scan_single(data):
    """Parse passphrase.html. Return (scan, hashes). hashes may be None."""
    scan = PageScan(inline=True)
    scan.feed(data.decode('utf-8'))
    scan.close()
    scripts, styles = scan.inline_text('script'), scan.inline_text('style')
    hashes = None
    if len(scripts) == 1 and len(styles) == 1:
        hashes = {'script-src': [csp_hash(scripts[0])], 'style-src': [csp_hash(styles[0])]}
    return scan, hashes


def check_single(data):
    """Check the bytes of passphrase.html. Return a list of problems."""
    scan, hashes = scan_single(data)
    problems = list(scan.problems)
    scripts, styles = scan.inline_text('script'), scan.inline_text('style')
    if len(scripts) != 1:
        problems.append(f'passphrase.html needs exactly one inline script, found {len(scripts)}')
    if len(styles) != 1:
        problems.append(f'passphrase.html needs exactly one inline style, found {len(styles)}')
    if scan.refs:
        problems.append('passphrase.html loads another file: ' + ', '.join(scan.refs))
    if len(scan.csp) != 1:
        problems.append('passphrase.html needs exactly one CSP meta element')
    for text in scan.csp:
        if hashes is None:
            problems += [f'meta {p}' for p in check_csp(text)]
        else:
            problems += [f'meta {p}' for p in check_csp(text, hashes=hashes)]
    for text in scripts:
        problems += check_js('inline script', text)
        match = re.search(r'^globalThis\.PASSPHRASE_DECK_WORDLIST = (".*");$', text, flags=re.MULTILINE)
        try:
            words = json.loads(match.group(1)) if match else None
        except ValueError:
            words = None
        if not isinstance(words, str) or sha256(words.encode('utf-8')) != verify_wordlist.SHA256:
            problems.append('inline script: the wordlist hash changed or the wordlist is missing')
    for text in styles:
        problems += check_css('inline style', text)
    return problems


# ----------------------------------------------------------- build verification

def read_tree(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.read_bytes()
            for p in sorted(folder.rglob('*')) if p.is_file()}


def check_assets_against(files, expected, ignore=()):
    problems = []
    for name, digest in expected.items():
        if name not in files:
            problems.append(f'missing file: {name}')
        elif sha256(files[name]) != digest:
            problems.append(f'checksum mismatch: {name}')
    for name in files:
        if name not in expected and name not in ignore:
            problems.append(f'unexpected file: {name}')
    return problems


def verify_build(out):
    """Check a build folder against its checksums and manifest."""
    out = Path(out)
    problems = []
    try:
        manifest = json.loads((out / 'release-manifest.json').read_text('utf-8'))
        lines = (out / 'SHA256SUMS').read_text('utf-8').splitlines()
    except (OSError, ValueError) as error:
        return [f'cannot read the manifest or checksums: {error}']
    listed = {}
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  (\S+)', line)
        if not match or '..' in match.group(2).split('/'):
            problems.append(f'bad checksum line: {line[:60]}')
            continue
        listed[match.group(2)] = match.group(1)
    for name, digest in listed.items():
        path = out / name
        if not path.is_file():
            problems.append(f'listed file is missing: {name}')
        elif sha256(path.read_bytes()) != digest:
            problems.append(f'checksum mismatch: {name}')
    expected = {f'site/{n}': d for n, d in manifest.get('assets', {}).items()}
    expected.update(manifest.get('artifacts', {}))
    single = manifest.get('single_file', {})
    expected.update(single)
    expected['release-manifest.json'] = sha256((out / 'release-manifest.json').read_bytes())
    if listed != expected:
        problems.append('SHA256SUMS does not match the manifest')
    site = read_tree(out / 'site')
    problems += check_assets_against(site, manifest.get('assets', {}))
    prefix = f'{manifest.get("name")}-{manifest.get("version")}'
    for kind in ('static', 'offline'):
        path = out / f'{prefix}-{kind}.zip'
        try:
            with zipfile.ZipFile(path) as archive:
                entries = {n: archive.read(n) for n in archive.namelist()}
        except (OSError, zipfile.BadZipFile) as error:
            problems.append(f'cannot read {path.name}: {error}')
            continue
        if kind == 'offline':
            entries = {n.split('/', 1)[1]: d for n, d in entries.items()
                       if n.startswith(prefix + '/')}
            if 'OFFLINE-USAGE.txt' not in entries:
                problems.append('offline zip has no usage file')
        # The static zip holds the site files. The offline zip holds the one file.
        wanted = single if kind == 'offline' else manifest.get('assets', {})
        problems += [f'{path.name}: {p}' for p in
                     check_assets_against(entries, wanted, ignore=('OFFLINE-USAGE.txt',))]
    problems += check_site(site)
    try:
        problems += check_single((out / 'passphrase.html').read_bytes())
    except OSError:
        problems.append('passphrase.html is missing')
    return problems


def check_folder(folder, manifest):
    """Check an unpacked offline folder or a site folder against a manifest."""
    files = read_tree(folder)
    if 'passphrase.html' in files:
        problems = check_assets_against(files, manifest.get('single_file', {}),
                                        ignore=('OFFLINE-USAGE.txt',))
        return problems + check_single(files['passphrase.html'])
    problems = check_assets_against(files, manifest['assets'], ignore=('OFFLINE-USAGE.txt',))
    files.pop('OFFLINE-USAGE.txt', None)
    return problems + check_site(files)


# --------------------------------------------------------- production verification

def check_headers(name, headers, hashes=None):
    """Check the response headers of one hosted file. Keys are lower case.

    The single file has a meta CSP. A header CSP is optional for it. If the
    host sends one, it must be as strict and must allow the same hashes.
    """
    problems = []
    page = name in ('index.html', 'passphrase.html')
    hsts = headers.get('strict-transport-security', '')
    match = re.search(r'max-age=(\d+)', hsts)
    if not match or int(match.group(1)) < HSTS_MIN:
        problems.append(f'{name}: Strict-Transport-Security max-age is missing or short')
    if headers.get('referrer-policy', '').strip().lower() != 'no-referrer':
        problems.append(f'{name}: Referrer-Policy must be no-referrer')
    if headers.get('x-content-type-options', '').strip().lower() != 'nosniff':
        problems.append(f'{name}: X-Content-Type-Options must be nosniff')
    csp = headers.get('content-security-policy')
    if name == 'index.html':
        if not csp:
            problems.append(f'{name}: Content-Security-Policy header is missing')
        else:
            problems += [f'{name}: header {p}' for p in check_csp(csp, header=True)]
    elif name == 'passphrase.html' and csp:
        problems += [f'{name}: header {p}' for p in check_csp(csp, header=True, hashes=hashes)]
    cache = headers.get('cache-control', '').lower()
    if page:
        if not re.search(r'no-cache|no-store|max-age=0', cache):
            problems.append(f'{name}: Cache-Control must force revalidation')
    else:
        age = re.search(r'max-age=(\d+)', cache)
        if 'immutable' not in cache or not age or int(age.group(1)) < IMMUTABLE_MIN:
            problems.append(f'{name}: Cache-Control must be long and immutable')
    kind = headers.get('content-type', '').lower()
    expected = ('text/html' if page else
                'javascript' if name.endswith('.js') else 'text/css')
    if expected not in kind:
        problems.append(f'{name}: Content-Type must be {expected}')
    return problems


def check_evidence(evidence, today=None):
    """Check the sanitized operator evidence. Return a list of problems."""
    today = today or date.today()
    problems = []

    def section(name):
        value = evidence.get(name) if isinstance(evidence, dict) else None
        if not isinstance(value, dict):
            problems.append(f'evidence section is missing: {name}')
            return {}
        return value

    def need_text(where, data, key):
        if not isinstance(data.get(key), str) or not data[key].strip():
            problems.append(f'{where}.{key} is missing')

    def need_date(where, data, key):
        try:
            if date.fromisoformat(str(data.get(key))) > today:
                problems.append(f'{where}.{key} is in the future')
        except ValueError:
            problems.append(f'{where}.{key} is not an ISO date')

    candidate = section('candidate')
    revision = candidate.get('revision')
    if not isinstance(revision, str) or not REVISION.fullmatch(revision):
        problems.append('candidate.revision must be a full Git revision')
    if not isinstance(candidate.get('manifest_sha256'), str) or \
            not DIGEST.fullmatch(candidate.get('manifest_sha256', '')):
        problems.append('candidate.manifest_sha256 is missing')
    need_text('candidate', candidate, 'version')
    assets = candidate.get('assets')
    if not isinstance(assets, dict) or list(assets) != ['passphrase.html'] or \
            not all(isinstance(d, str) and DIGEST.fullmatch(d) for d in assets.values()):
        problems.append('candidate.assets must map passphrase.html to its SHA-256 sum')

    review = section('review')
    if review.get('candidate_revision') != revision:
        problems.append('review is not for the candidate revision')
    need_date('review', review, 'date')
    need_text('review', review, 'reviewer_role')
    if review.get('disposition') != 'approved':
        problems.append('review.disposition must be approved')
    if review.get('unresolved_findings') != 0:
        problems.append('review.unresolved_findings must be 0')

    devices = evidence.get('devices') if isinstance(evidence, dict) else None
    found = {}
    for item in devices if isinstance(devices, list) else []:
        if isinstance(item, dict):
            found[item.get('platform')] = item
    for platform in PLATFORMS:
        item = found.get(platform)
        if item is None:
            problems.append(f'device evidence is missing: {platform}')
            continue
        where = f'devices[{platform}]'
        if item.get('candidate_revision') != revision:
            problems.append(f'{where} is not for the candidate revision')
        if item.get('real_device') is not True:
            problems.append(f'{where} must be a real device')
        if item.get('result') != 'pass':
            problems.append(f'{where}.result must be pass')
        if item.get('offline_result') != 'pass':
            problems.append(f'{where}.offline_result must be pass')
        for key in ('os_version', 'mode_tested', 'install_behavior'):
            need_text(where, item, key)
        need_date(where, item, 'date')

    deployment = section('deployment')
    if deployment.get('deployed_revision') != revision:
        problems.append('deployment is not the candidate revision')
    if deployment.get('authorized') is not True:
        problems.append('deployment.authorized must be true')
    need_text('deployment', deployment, 'authorized_by_role')
    need_text('deployment', deployment, 'url')
    need_date('deployment', deployment, 'date')
    return problems


def default_fetch(url):
    """GET a URL with full TLS checks. Return (status, headers, body, final URL)."""
    request = urllib.request.Request(url, headers={'User-Agent': 'passphrase-deck-verifier'})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        headers = {k.lower(): v for k, v in response.headers.items()}
        return response.status, headers, response.read(), response.geturl()


def verify_production(url, evidence, manifest=None, fetch=default_fetch, today=None):
    """Compare the hosted files with the reviewed candidate. Return problems."""
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.query or parsed.fragment \
            or not parsed.path.endswith('/passphrase.html'):
        return ['the production URL must be https and end with /passphrase.html']
    problems = check_evidence(evidence, today)
    candidate = evidence.get('candidate', {}) if isinstance(evidence, dict) else {}
    expected = candidate.get('assets') if isinstance(candidate.get('assets'), dict) else {}
    if manifest is not None:
        if manifest.get('single_file') != expected:
            problems.append('the manifest single file differs from the candidate evidence')
        expected = manifest.get('single_file', {})
    deployed = evidence.get('deployment', {}) if isinstance(evidence, dict) else {}
    if isinstance(deployed, dict) and deployed.get('url') not in (None, url):
        problems.append('deployment.url differs from the verified URL')
    if list(expected) != ['passphrase.html']:
        return problems + ['no reviewed passphrase.html sum to compare']
    name = 'passphrase.html'
    try:
        status, headers, body, final = fetch(url)
    except (OSError, ssl.SSLError, ValueError) as error:
        return problems + [f'{name}: request failed: {type(error).__name__}']
    if status != 200 or final != url:
        return problems + [f'{name}: status {status} or redirect away from the URL']
    try:
        _, hashes = scan_single(body)
    except ValueError:
        return problems + [f'{name}: hosted bytes are not valid UTF-8 text']
    problems += check_headers(name, headers, hashes)
    if sha256(body) != expected[name]:
        problems.append(f'{name}: hosted bytes differ from the reviewed release')
    problems += [f'hosted {p}' for p in check_single(body)]
    return problems


# ------------------------------------------------------------------- self test

def good_headers(name):
    base = {
        'strict-transport-security': 'max-age=31536000',
        'referrer-policy': 'no-referrer',
        'x-content-type-options': 'nosniff',
    }
    if name in ('index.html', 'passphrase.html'):
        base.update({
            'content-type': 'text/html; charset=utf-8',
            'cache-control': 'no-cache',
        })
        if name == 'index.html':
            base['content-security-policy'] = (
                "default-src 'none'; script-src 'self'; style-src 'self'; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
    else:
        base.update({
            'content-type': 'text/css' if name.endswith('.css') else 'text/javascript',
            'cache-control': 'public, max-age=31536000, immutable',
        })
    return base


def self_test():
    failures = []

    def expect(label, condition):
        if not condition:
            failures.append(label)

    def has(problems, text):
        return any(text in p for p in problems)

    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        first = package_release.build(Path(one) / 'a')
        second = package_release.build(Path(two) / 'b')
        expect('manifests match', first == second)
        tree_a, tree_b = read_tree(Path(one) / 'a'), read_tree(Path(two) / 'b')
        expect('output bytes match', tree_a == tree_b and len(tree_a) == 9)
        build_a = Path(one) / 'a'
        expect('build verifies', verify_build(build_a) == [])
        expect('site passes static checks', check_site(read_tree(build_a / 'site')) == [])
        expect('folder check passes', check_folder(build_a / 'site', first) == [])
        single_bytes = (build_a / 'passphrase.html').read_bytes()
        expect('single file passes static checks', check_single(single_bytes) == [])
        with tempfile.TemporaryDirectory() as unpacked:
            prefix = f'{first["name"]}-{first["version"]}'
            with zipfile.ZipFile(next(build_a.glob('*-offline.zip'))) as archive:
                for entry in archive.namelist():
                    (Path(unpacked) / entry.split('/', 1)[1]).write_bytes(archive.read(entry))
            expect('offline folder passes', check_folder(unpacked, first) == [])
            expect('offline zip holds the one file',
                   sorted(p.name for p in Path(unpacked).iterdir()) == ['OFFLINE-USAGE.txt', 'passphrase.html'])
            (Path(unpacked) / 'passphrase.html').write_bytes(single_bytes + b' ')
            expect('offline folder change found', check_folder(unpacked, first) != [])
        try:
            package_release.build(package_release.ROOT / 'build-test-output')
            expect('refuses output inside the repository', False)
        except ValueError:
            pass

        # A changed asset must be found in the site, a zip, and the sums.
        for victim in sorted((build_a / 'site').iterdir()) + [build_a / 'passphrase.html']:
            original = victim.read_bytes()
            victim.write_bytes(original + b' ')
            expect(f'changed asset found: {victim.name}', has(verify_build(build_a), 'mismatch'))
            victim.write_bytes(original)
        zip_path = next(build_a.glob('*-offline.zip'))
        original = zip_path.read_bytes()
        zip_path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        expect('changed zip found', verify_build(build_a) != [])
        zip_path.write_bytes(original)
        (build_a / 'site' / 'extra.js').write_text('x', encoding='utf-8')
        expect('extra file found', has(verify_build(build_a), 'unexpected file'))
        (build_a / 'site' / 'extra.js').unlink()
        expect('build verifies again', verify_build(build_a) == [])

        site = read_tree(build_a / 'site')
        html = site['index.html'].decode('utf-8')

        # Static check cases. Each bad input must be found.
        def mutated(old, new):
            changed = dict(site)
            changed['index.html'] = html.replace(old, new, 1).encode('utf-8')
            return check_site(changed)

        expect('inline script found', has(mutated('</head>', '<script>alert(1)</script></head>'), 'inline'))
        expect('event handler found', has(mutated('<main>', '<main onclick="x()">'), 'event handler'))
        expect('inline style found', has(mutated('<main>', '<main style="color:red">'), 'inline style'))
        expect('external script found', has(mutated('</head>', '<script src="https://example.com/a.js"></script></head>'), 'external script'))
        expect('external stylesheet found', has(mutated('</head>', '<link rel="stylesheet" href="//example.com/a.css"></head>'), 'external link'))
        expect('unsafe CSP found', has(mutated("script-src 'self'", "script-src 'self' 'unsafe-inline'"), 'CSP'))
        expect('connect allowance found', has(mutated("default-src 'none';", "default-src 'none'; connect-src 'self';"), 'connect-src'))
        expect('missing CSP found', has(mutated('Content-Security-Policy', 'X-Other'), 'CSP'))
        expect('iframe found', has(mutated('<main>', '<main><iframe></iframe>'), 'iframe'))
        deck = next(n for n in site if n.startswith('deck.'))
        for label, extra in (('eval', 'eval("1");'), ('xhr', 'new XMLHttpRequest();'),
                             ('absolute URL', 'var u = "https://example.com/";'),
                             ('external fetch', 'fetch("https://example.com/");'),
                             ('dynamic fetch', 'fetch(target);'),
                             ('HTML sink', 'x.innerHTML = 1;')):
            changed = dict(site)
            changed[deck] = site[deck] + ('\n' + extra).encode()
            expect(f'script check found {label}', check_site(changed) != [])
        css = next(n for n in site if n.endswith('.css'))
        changed = dict(site)
        changed[css] = site[css] + b'\n@import url("https://example.com/a.css");'
        expect('css import found', has(check_site(changed), 'css'))

        # Single-file check cases. Each bad input must be found.
        page = single_bytes.decode('utf-8')

        def single_mutated(old, new, fix=False):
            changed = page.replace(old, new, 1)
            if fix:  # make the CSP hashes match the new blocks, to test the other checks
                scan, hashes = scan_single(changed.encode('utf-8'))
                csp = scan.csp[0]
                new_csp = re.sub(r"script-src [^;]*", 'script-src ' + hashes['script-src'][0], csp)
                new_csp = re.sub(r"style-src [^;]*", 'style-src ' + hashes['style-src'][0], new_csp)
                changed = changed.replace(csp, new_csp, 1)
            return check_single(changed.encode('utf-8'))

        expect('single: injected inline script found',
               has(single_mutated('</body>', '<script>alert(1)</script></body>'), 'inline script'))
        expect('single: injected inline style found',
               has(single_mutated('</head>', '<style>a{}</style></head>'), 'inline style'))
        expect('single: changed script found by hash',
               has(single_mutated('use strict', 'use  strict'), 'script-src'))
        expect('single: changed style found by hash',
               has(single_mutated('<style>\n', '<style>\n/* x */'), 'style-src'))
        expect('single: event handler found', has(single_mutated('<main>', '<main onclick="x()">'), 'event handler'))
        expect('single: inline style attribute found', has(single_mutated('<main>', '<main style="a:b">'), 'inline style'))
        expect('single: external script found',
               has(single_mutated('</head>', '<script src="https://example.com/a.js"></script></head>'), 'external script'))
        expect('single: local script file found',
               has(single_mutated('</head>', '<script src="a.js"></script></head>'), 'loads another file'))
        expect('single: external link found',
               has(single_mutated('</head>', '<link rel="stylesheet" href="//example.com/a.css"></head>'), 'external link'))
        expect('single: unsafe-inline found', has(single_mutated("script-src ", "script-src 'unsafe-inline' "), 'CSP'))
        expect('single: self source found', has(single_mutated("style-src ", "style-src 'self' "), 'CSP'))
        expect('single: connect-src found',
               has(single_mutated("default-src 'none';", "default-src 'none'; connect-src 'self';"), 'connect-src'))
        expect('single: missing CSP found', has(single_mutated('Content-Security-Policy', 'X-Other'), 'CSP'))
        expect('single: iframe found', has(single_mutated('<main>', '<main><iframe></iframe>'), 'iframe'))
        expect('single: eval found', has(single_mutated('use strict', 'use strict\'; eval("1"); \'', fix=True), 'eval'))
        expect('single: absolute URL found',
               has(single_mutated('use strict', 'use strict\'; var u = "https://example.com/"; \'', fix=True), 'absolute URL'))
        expect('single: wordlist change found',
               has(single_mutated('abacus', 'abacuz', fix=True), 'wordlist'))
        expect('single: css import found',
               has(single_mutated('<style>\n', '<style>\n@import url("https://example.com/a.css");', fix=True), '@import'))

        # Header checks.
        for name in list(site) + ['passphrase.html']:
            expect(f'good headers pass: {name}', check_headers(name, good_headers(name)) == [])
            for key in list(good_headers(name)):
                broken = good_headers(name)
                del broken[key]
                expect(f'missing {key} found: {name}', check_headers(name, broken) != [])
        weak = good_headers('index.html')
        weak['content-security-policy'] = weak['content-security-policy'].replace("; frame-ancestors 'none'", '')
        expect('missing frame-ancestors found', check_headers('index.html', weak) != [])
        _, page_hashes = scan_single(single_bytes)
        with_csp = good_headers('passphrase.html')
        with_csp['content-security-policy'] = (
            f"default-src 'none'; script-src {page_hashes['script-src'][0]}; "
            f"style-src {page_hashes['style-src'][0]}; base-uri 'none'; form-action 'none'; "
            "frame-ancestors 'none'")
        expect('header CSP with hashes passes', check_headers('passphrase.html', with_csp, page_hashes) == [])
        with_csp['content-security-policy'] = with_csp['content-security-policy'].replace("script-src '", "script-src 'unsafe-inline' '")
        expect('header CSP with unsafe-inline found', check_headers('passphrase.html', with_csp, page_hashes) != [])
        with_csp['content-security-policy'] = good_headers('index.html')['content-security-policy']
        expect('header CSP with self found', check_headers('passphrase.html', with_csp, page_hashes) != [])

        # Evidence checks.
        revision = 'a' * 40
        today = date(2030, 1, 1)

        def make_evidence():
            device = lambda platform: {
                'platform': platform, 'real_device': True, 'result': 'pass',
                'offline_result': 'pass', 'os_version': 'test', 'mode_tested': 'browser tab',
                'install_behavior': 'home screen shortcut works', 'date': '2029-12-01',
                'candidate_revision': revision}
            return {
                'candidate': {'revision': revision, 'version': first['version'],
                              'manifest_sha256': sha256(b'm'), 'assets': dict(first['single_file'])},
                'review': {'candidate_revision': revision, 'date': '2029-12-01',
                           'reviewer_role': 'independent reviewer', 'disposition': 'approved',
                           'unresolved_findings': 0},
                'devices': [device(p) for p in PLATFORMS],
                'deployment': {'deployed_revision': revision, 'authorized': True,
                               'authorized_by_role': 'owner', 'url': 'https://example.test/p/passphrase.html',
                               'date': '2029-12-02'},
            }

        expect('good evidence passes', check_evidence(make_evidence(), today) == [])
        expect('empty evidence refused', check_evidence({}, today) != [])
        for section_name in ('candidate', 'review', 'devices', 'deployment'):
            broken = make_evidence()
            del broken[section_name]
            expect(f'missing {section_name} refused', check_evidence(broken, today) != [])
        cases = {
            'review revision mismatch': lambda e: e['review'].update(candidate_revision='b' * 40),
            'review not approved': lambda e: e['review'].update(disposition='rejected'),
            'open findings': lambda e: e['review'].update(unresolved_findings=1),
            'review date missing': lambda e: e['review'].pop('date'),
            'iOS missing': lambda e: e['devices'].pop(0),
            'Android missing': lambda e: e['devices'].pop(1),
            'device failed': lambda e: e['devices'][0].update(result='fail'),
            'device offline failed': lambda e: e['devices'][1].update(offline_result='fail'),
            'emulator only': lambda e: e['devices'][0].update(real_device=False),
            'device revision mismatch': lambda e: e['devices'][1].update(candidate_revision='b' * 40),
            'install note missing': lambda e: e['devices'][0].pop('install_behavior'),
            'deployed revision mismatch': lambda e: e['deployment'].update(deployed_revision='b' * 40),
            'not authorized': lambda e: e['deployment'].update(authorized=False),
            'asset digest bad': lambda e: e['candidate']['assets'].update({'passphrase.html': 'zz'}),
            'extra asset listed': lambda e: e['candidate']['assets'].update({'index.html': sha256(b'x')}),
        }
        for label, change in cases.items():
            broken = make_evidence()
            change(broken)
            expect(f'evidence refused: {label}', check_evidence(broken, today) != [])

        # Production flow with a fake host that serves the built site.
        evidence = make_evidence()
        url = 'https://example.test/p/passphrase.html'
        evidence['deployment']['url'] = url
        files = {'passphrase.html': single_bytes}

        def host(files=files, drop=None, final=None, extra=None):
            def fetch(target):
                headers = good_headers('passphrase.html')
                headers.update(extra or {})
                if drop:
                    headers.pop(drop, None)
                if target != url or 'passphrase.html' not in files:
                    return 404, headers, b'', target
                return 200, headers, files['passphrase.html'], final or target
            return fetch

        run = lambda **kw: verify_production(url, kw.pop('evidence', evidence), fetch=host(**kw), today=today)
        manifest_ok = lambda: verify_production(url, evidence, first, host(), today)
        expect('production passes', run() == [])
        expect('production passes with the manifest', manifest_ok() == [])
        expect('production http refused', verify_production(
            'http://example.test/p/passphrase.html', evidence, fetch=host(), today=today) != [])
        expect('production slash URL refused', verify_production(
            'https://example.test/p/', evidence, fetch=host(), today=today) != [])
        changed = {'passphrase.html': single_bytes + b'\n<!-- changed -->'}
        expect('production byte mismatch found', has(run(files=changed), 'differ'))
        injected = {'passphrase.html': single_bytes.replace(b'</body>', b'<script>x()</script></body>', 1)}
        expect('production injected script found', has(run(files=injected), 'inline script'))
        expect('production header missing found', has(run(drop='strict-transport-security'), 'Strict'))
        expect('production redirect found', run(final='https://other.test/') != [])
        expect('production missing file found', run(files={}) != [])
        expect('production bad header CSP found',
               has(run(extra={'content-security-policy': "default-src 'none'; script-src 'self'"}), 'header CSP'))
        broken = make_evidence()
        broken['devices'].pop()
        expect('production refuses missing device evidence', run(evidence=broken) != [])
        expect('production refuses missing evidence', run(evidence={}) != [])

        def refuse(target):
            raise ssl.SSLError('bad certificate')

        expect('production TLS failure found', verify_production(url, evidence, fetch=refuse, today=today) != [])

    for label in failures:
        print(f'FAIL: {label}', file=sys.stderr)
    if failures:
        return 1
    print('verify_release self-test: all checks passed')
    return 0


def report(problems, ok_text):
    for problem in problems:
        print(f'FAIL: {problem}', file=sys.stderr)
    if problems:
        return 1
    print(ok_text)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--verify', metavar='OUT')
    parser.add_argument('--check-folder', metavar='DIR')
    parser.add_argument('--production', metavar='URL')
    parser.add_argument('--evidence', metavar='FILE')
    parser.add_argument('--manifest', metavar='FILE')
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            return self_test()
        if args.verify:
            return report(verify_build(args.verify), 'Build folder verified.')
        manifest = json.loads(Path(args.manifest).read_text('utf-8')) if args.manifest else None
        if args.check_folder:
            if manifest is None:
                parser.error('--check-folder needs --manifest')
            return report(check_folder(args.check_folder, manifest), 'Folder verified.')
        if args.production:
            if not args.evidence:
                parser.error('--production needs --evidence')
            evidence = json.loads(Path(args.evidence).read_text('utf-8'))
            return report(verify_production(args.production, evidence, manifest),
                          'Production release verified.')
    except (OSError, ValueError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    parser.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
