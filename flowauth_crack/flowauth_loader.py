#!/usr/bin/env python3
"""FlowAuth loader front-half -- the *generalizable* part of the fetch.

Given ANY ``https://flowauth.net/v1/loaders/<md5>.lua`` URL this module does,
in pure Python (stdlib only, no sandbox needed):

  1. GET the loader with the Roblox HttpGet headers the server gates on
     (a plain GET is answered with a 266-byte decoy that decodes to
     "FlowAuth: automated source fetching is not allowed.").
  2. Parse the loader: decode its decimal-escaped strings to recover the
     stage-2 runtime URL(s), the expected runtime size, the Adler checksum
     target, and the two ``_bsdata0`` handoff literals (normal / alternate).
  3. Fetch the stage-2 Luraph runtime from the content-addressed URL (with an
     IP fallback + cache-buster variants) and VERIFY it against the size and
     the loader's own 8-byte-stepped Adler-32.

Everything here is script-agnostic: nothing is pinned to one ``<md5>``.  The
only step that still needs the Luau sandbox is *executing* that runtime to run
the session-keyed auth handshake -- that lives in ``flowauth_two_phase.py``.

Run standalone to inspect / fetch a runtime for any URL:

    python3 flowauth_loader.py https://flowauth.net/v1/loaders/<md5>.lua [-o runtime.lua]
"""
import os
import re
import sys
import urllib.error
import urllib.request

# The FlowAuth server only serves the real loader to a request that looks like
# Roblox's HttpGet; anything else gets the "automated source fetching is not
# allowed" decoy.  These are the same headers the live chain uses.
ROBLOX_HEADERS = {
    "User-Agent": "Roblox/Win32",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-FlowAuth-Protocol": "3",
}

# Text of the anti-automation decoy body (decoded from its \ddd escapes).
DECOY_MARKER = "automated source fetching is not allowed"

_ESCAPE_RE = re.compile(r"\\(\d{1,3})")


class LoaderError(Exception):
    """A FlowAuth loader could not be fetched or parsed."""


def decode_escapes(s):
    """Decode a Lua decimal-escaped string body (``\\104\\116...``) to text."""
    return _ESCAPE_RE.sub(lambda m: chr(int(m.group(1))), s)


def http_get(url, timeout=30, headers=None):
    """GET ``url`` with the Roblox headers; return (status, bytes)."""
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or ROBLOX_HEADERS).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_loader(url, timeout=30):
    """Fetch a loader ``<md5>.lua`` and return its source text.

    Raises ``LoaderError`` on a non-200, on the anti-automation decoy, or on a
    body that is not a FlowAuth loader.
    """
    status, raw = http_get(url, timeout=timeout)
    if status != 200:
        raise LoaderError("loader fetch failed: HTTP %d (%s)" % (status, url))
    text = raw.decode("latin1")
    if DECOY_MARKER in decode_escapes(text):
        raise LoaderError(
            "server returned the anti-automation decoy for %s -- the real loader "
            "is only served with Roblox HttpGet headers; this request sent them, "
            "so the URL is likely rate-limited or the <md5> is invalid/expired" % url)
    if "local handoff=" not in text and "FlowAuth" not in text:
        raise LoaderError("response is not a FlowAuth loader (%d B): %r" % (len(text), text[:80]))
    return text


def adler_flow(data):
    """The loader's own checksum: Adler-32 walked eight bytes at a time.

    Mirrors the ``accept()`` routine in the loader exactly so we can verify a
    downloaded runtime the same way the loader would before compiling it.
    """
    if isinstance(data, str):
        data = data.encode("latin1")
    s1, s2, i, n = 1, 0, 0, len(data)
    while i + 8 <= n:
        a, b, c, d, e, f, g, h = data[i:i + 8]
        s2 = (s2 + 8 * s1 + 8 * a + 7 * b + 6 * c + 5 * d + 4 * e + 3 * f + 2 * g + h) % 65521
        s1 = (s1 + a + b + c + d + e + f + g + h) % 65521
        i += 8
    while i < n:
        s1 = (s1 + data[i]) % 65521
        s2 = (s2 + s1) % 65521
        i += 1
    return s2 * 65536 + s1


class LoaderInfo(object):
    """Everything the fetch needs, recovered from a loader's source."""

    def __init__(self, md5, stage2_candidates, expected_size, adler_target,
                 handoff_normal, handoff_alternate):
        self.md5 = md5
        self.stage2_candidates = stage2_candidates      # ordered, primary first
        self.expected_size = expected_size
        self.adler_target = adler_target
        self.handoff_normal = handoff_normal            # Lua literal, `or` branch
        self.handoff_alternate = handoff_alternate      # Lua literal, `and` branch

    def __repr__(self):
        return ("LoaderInfo(md5=%s, size=%s, adler=%s, candidates=%d)"
                % (self.md5, self.expected_size, self.adler_target,
                   len(self.stage2_candidates)))


def _decoded_string_literal(src, name):
    """Decode ``local <name>="\\ddd..."`` from the loader, or return None."""
    m = re.search(r'local %s="((?:\\\d{1,3})+)"' % re.escape(name), src)
    return decode_escapes(m.group(1)) if m else None


def parse_loader(src, loader_url=""):
    """Parse a loader's source into a :class:`LoaderInfo` (no network)."""
    url = _decoded_string_literal(src, "url")
    if not url:
        raise LoaderError("loader has no stage-2 `url` string")
    fallback = _decoded_string_literal(src, "fallback") or ""

    m = re.search(r'local expected=(\d+)', src)
    if not m:
        raise LoaderError("loader has no `expected` size")
    expected_size = int(m.group(1))

    m = re.search(r'~=(\d+)\s*then problem\("runtime checksum', src)
    if not m:
        raise LoaderError("loader has no runtime checksum target")
    adler_target = int(m.group(1))

    # The loader appends a cache-buster and, for the sha256-addressed host, also
    # tries a path-stripped "retry" URL. Re-derive the same set, primary first.
    retry_q = re.search(r'\?retry=[0-9a-f]+', src)
    retry_q = retry_q.group(0) if retry_q else ""
    candidates = [url]
    if retry_q:
        candidates.append(url + retry_q)                                    # pinned
        candidates.append(re.sub(r"/sha256/[a-f0-9]+/", "/", url) + retry_q)  # retry
    if fallback:
        candidates.append(fallback)                                         # IP fallback
    # de-dup, keep order
    seen, ordered = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)

    # _bsdata0 handoff: `local handoff=alternate and {A,..} or {B,..}`.
    # patch_envlog installs the NORMAL (non-alternate) variant = the `or` branch,
    # which is what the primary content-addressed fetch corresponds to.
    handoff_normal = handoff_alternate = None
    hline = next((l for l in src.splitlines() if l.startswith("local handoff=")), None)
    if hline:
        idx = hline.find("} or {")
        if idx > 0:
            alt = hline[len("local handoff="):idx + 1].strip()
            alt = alt[len("alternate and"):].strip() if alt.startswith("alternate and") else alt
            handoff_alternate = alt
            handoff_normal = hline[idx + 5:].rstrip()

    md5 = ""
    m = re.search(r"/v1/loaders/([0-9a-f]{32})\.lua", loader_url)
    if m:
        md5 = m.group(1)

    return LoaderInfo(md5, ordered, expected_size, adler_target,
                      handoff_normal, handoff_alternate)


def fetch_runtime(info, timeout=40, log=print):
    """Fetch + verify the stage-2 runtime; return (bytes, used_alternate_url).

    Tries each candidate URL in order and accepts the first whose body matches
    both the expected size and the loader's Adler checksum.
    """
    problems = []
    for idx, url in enumerate(info.stage2_candidates):
        try:
            status, data = http_get(url, timeout=timeout)
        except Exception as e:                       # noqa: BLE001 - report & try next
            problems.append("%s -> %s" % (url, e))
            continue
        if status != 200:
            problems.append("%s -> HTTP %d" % (url, status))
            continue
        if len(data) != info.expected_size:
            problems.append("%s -> %d B (expected %d)" % (url, len(data), info.expected_size))
            continue
        got = adler_flow(data)
        if got != info.adler_target:
            problems.append("%s -> checksum %d (expected %d)" % (url, got, info.adler_target))
            continue
        if log:
            log("    runtime OK: %d B, checksum %d, via %s"
                % (len(data), got, "primary" if idx == 0 else url))
        # a non-primary hit means the loader would have set alternate=true
        return data, idx != 0
    raise LoaderError("no stage-2 runtime URL verified:\n  " + "\n  ".join(problems))


# --------------------------------------------------------------------------- #
#  Sandbox-repo discovery (the Luau runtime + envlog sandbox live in the       #
#  Deobfuscator-Luraph-V15 repo, referenced by path).  Make that path          #
#  discoverable instead of hardcoded so the fetcher runs on any machine.       #
# --------------------------------------------------------------------------- #
_REPO_BASENAMES = ("Deobfuscator-Luraph-V15", "deobfuscator-luraph-v15")


def _looks_like_repo(path):
    return bool(path) and os.path.isdir(path) and \
        os.path.exists(os.path.join(path, "core", "harness.py")) and \
        os.path.exists(os.path.join(path, "runtime", "envlog.luau"))


def find_repo(explicit=None):
    """Locate the Deobfuscator-Luraph-V15 repo (luau + envlog sandbox).

    Order: explicit arg, ``FLOWAUTH_REPO`` env, then common sibling locations
    relative to this FlowAuth repo and the home directory.  Raises with a clear
    message (and the list of places tried) when none is found.
    """
    here = os.path.dirname(os.path.abspath(__file__))       # flowauth_crack/
    flow_root = os.path.dirname(here)                        # FlowAuth-Deobfuscator/
    parent = os.path.dirname(flow_root)
    home = os.path.expanduser("~")

    bases = (parent, home, os.path.join(home, "my-project"), "/home/z/my-project")
    tried = []
    candidates = [explicit, os.environ.get("FLOWAUTH_REPO")]
    for base in bases:
        for name in _REPO_BASENAMES:
            candidates.append(os.path.join(base, name))
    # shallow scan: the repo may sit one level deeper (e.g. a nested clone like
    # <base>/<owner>/deobfuscator-luraph-v15), so glance inside each base too.
    for base in bases:
        try:
            subdirs = sorted(os.listdir(base))
        except OSError:
            continue
        for sub in subdirs:
            for name in _REPO_BASENAMES:
                candidates.append(os.path.join(base, sub, name))
    for cand in candidates:
        if not cand:
            continue
        cand = os.path.abspath(os.path.expanduser(cand))
        if cand in tried:
            continue
        tried.append(cand)
        if _looks_like_repo(cand):
            return cand
    raise LoaderError(
        "Deobfuscator-Luraph-V15 repo not found (needs core/harness.py + "
        "runtime/envlog.luau + bin/luau).\nSet FLOWAUTH_REPO or pass --repo. "
        "Tried:\n  " + "\n  ".join(tried))


def build_bootstrapper(runtime_src, long_string):
    """Wrap a verified runtime so the sandbox runs it like the loader would.

    ``credential = nil`` (a bare ``loadstring(HttpGet(url))()`` passes no
    argument) and ``_bsdata0`` is preseeded by patch_envlog, so the loader
    itself never has to run.  ``long_string`` is ``harness.long_string``.
    """
    return (
        "-- [SUPERZ] FlowAuth bootstrapper: run the verified runtime directly\n"
        "-- (credential = nil, _bsdata0 preseeded by patch_envlog.py)\n"
        "local __SZ_RUNTIME = " + long_string(runtime_src) + "\n"
        'local __SZ_F = loadstring(__SZ_RUNTIME, "=FlowAuthRuntime")\n'
        'if type(__SZ_F) ~= "function" then error("FlowAuthRuntime compile failed") end\n'
        "return __SZ_F()\n"
    )


def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Fetch + verify a FlowAuth stage-2 runtime for any loader URL")
    ap.add_argument("loader_url", help="https://flowauth.net/v1/loaders/<md5>.lua")
    ap.add_argument("-o", "--out", help="write the verified runtime here")
    args = ap.parse_args(argv)

    print("[*] fetching loader:", args.loader_url)
    src = fetch_loader(args.loader_url)
    info = parse_loader(src, args.loader_url)
    print("[*] parsed:", info)
    print("    primary stage-2:", info.stage2_candidates[0])
    print("[*] fetching + verifying runtime ...")
    data, used_alt = fetch_runtime(info)
    print("[+] runtime verified: %d B%s" % (len(data), " (via fallback URL)" if used_alt else ""))
    if args.out:
        with open(args.out, "wb") as f:
            f.write(data)
        print("[+] written:", args.out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main(sys.argv[1:]))
    except LoaderError as e:
        sys.exit("error: %s" % e)
