#!/usr/bin/env python3
"""In-process FlowAuth chain -- fetch the obfuscated payload behind ANY
``https://flowauth.net/v1/loaders/<md5>.lua`` URL, in one luau process.

What it does, driven entirely by the loader URL (nothing is pinned to one
script):

  0. GET the loader (Roblox HttpGet headers -- the server serves a decoy
     otherwise), decode it, and recover the stage-2 runtime URL, its size and
     checksum, and the _bsdata0 handoff  (flowauth_loader.py).
  1. Download + VERIFY the stage-2 Luraph runtime (size + the loader's own
     Adler-32), then wrap it as a bootstrapper.
  2. Patch the envlog sandbox with the loader's handoff + crypto/JSON shims
     (patch_envlog.py) and start ONE luau process for the whole session.
  3. The runtime leaks every HTTP hop (\\1SUPERZREQ\\1 marker: base64
     "method|url|body") and SUSPENDS the run (__LRMRES yield); this driver
     answers the hop LIVE, plants the response (serve mode "plant") and
     resumes the exact thread. Same process = same session nonce, so the
     payload response authentication holds (cross-run replay never works).
  4. When the run finishes, every loadstring'd chunk (the Luraph-protected
     payload) is captured, then reassembled into the raw payload source.

The Luau sandbox (bin/luau + runtime/envlog.luau + core/harness.py) lives in
the Deobfuscator-Luraph-V15 repo; it is auto-discovered (--repo / FLOWAUTH_REPO
/ sibling paths).

Usage:
    python3 flowauth_two_phase.py [max_hops] \\
        [--loader-url https://flowauth.net/v1/loaders/<md5>.lua] [--repo PATH]
"""
import argparse
import base64
import importlib
import os
import re
import select
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import flowauth_loader as fl

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
DEFAULT_LOADER_URL = "https://flowauth.net/v1/loaders/29f4f4b924aff467652814456286bb05.lua"
HDRS = {"Content-Type": "application/json", "Accept": "application/json",
        "X-FlowAuth-Protocol": "3", "User-Agent": "Roblox/Win32"}
B64RE = re.compile("\x01SUPERZREQ\x01([A-Za-z0-9+/=]+)")

# Set by setup_repo() once the sandbox repo is discovered.
harness = None
REPO = LUAU = BOOT = None


def setup_repo(repo_arg=None):
    """Discover the Deobfuscator-Luraph-V15 repo and wire up harness/luau."""
    global harness, REPO, LUAU, BOOT
    REPO = fl.find_repo(repo_arg)
    sys.path.insert(0, os.path.join(REPO, "core"))
    harness = importlib.import_module("harness")
    LUAU = harness.find_luau()
    BOOT = os.path.join(WORK, "bootstrapper.lua")
    print("[*] sandbox repo: %s" % REPO)


def http(method, url, body=None):
    req = urllib.request.Request(url, data=body.encode("latin1") if body else None, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("latin1"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("latin1"), dict(e.headers)


def refresh_loader(loader_url):
    """Fetch a FRESH loader for ``loader_url``, download + verify its stage-2
    runtime, build the bootstrapper, and re-patch envlog with the loader's
    handoff + an empty canned map. Returns the parsed :class:`LoaderInfo`.

    The loader's _bsdata0 launch_ticket is single-use (a replayed challenge is
    rejected 401 launch_ticket_rejected), so every run starts from a fresh one.
    """
    os.makedirs(WORK, exist_ok=True)
    open(os.path.join(WORK, "canned.json"), "w").write("{}")

    src = fl.fetch_loader(loader_url)
    info = fl.parse_loader(src, loader_url)
    loader_p = os.path.join(WORK, "loader.lua")
    open(loader_p, "w", encoding="latin1").write(src)
    print("[0] fresh loader: %d B (md5 %s, handoff ticket refreshed)"
          % (len(src), info.md5 or "?"))

    runtime, used_alt = fl.fetch_runtime(info)
    open(os.path.join(WORK, "runtime_marbeg.lua"), "wb").write(runtime)
    if used_alt:
        print("    [!] runtime came from a fallback URL; envlog uses the normal "
              "handoff -- if auth fails, the alternate handoff may be needed")
    boot = fl.build_bootstrapper(runtime.decode("latin1"), harness.long_string)
    with open(BOOT, "w", encoding="latin1", newline="\n") as f:
        f.write(boot)
    print("    bootstrapper %d B (runtime %d B)" % (len(boot), len(runtime)))

    r = subprocess.run([sys.executable, os.path.join(HERE, "patch_envlog.py"),
                        "--repo", REPO, "--loader", loader_p,
                        "--canned", os.path.join(WORK, "canned.json")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("patch failed: " + r.stdout + r.stderr)
    print("    " + r.stdout.strip().replace("\n", "\n    "))
    return info


def reassemble(info):
    """Reassemble the captured chunks into the raw payload source and copy it
    to an md5-named file. Returns the payload path or None."""
    import reassemble_payload
    try:
        reassemble_payload.main()
    except SystemExit as e:
        if e.code:
            print("    [!] reassembly skipped: %s" % e.code)
            return None
    payload = os.path.join(WORK, "payload_source.lua")
    if not os.path.exists(payload):
        return None
    if info.md5:
        named = os.path.join(WORK, "%s.payload.lua" % info.md5)
        with open(payload, "rb") as s, open(named, "wb") as d:
            d.write(s.read())
        return named
    return payload


def main():
    ap = argparse.ArgumentParser(description="FlowAuth one-process live chain -- any loader URL")
    ap.add_argument("hops", nargs="?", type=int, default=24, help="max HTTP hops (default 24)")
    ap.add_argument("--loader-url", default=DEFAULT_LOADER_URL,
                    help="any flowauth.net /v1/loaders/<md5>.lua URL")
    ap.add_argument("--repo", default=None,
                    help="Deobfuscator-Luraph-V15 repo (else FLOWAUTH_REPO / auto-discover)")
    args = ap.parse_args()
    max_hops = args.hops

    try:
        setup_repo(args.repo)
    except fl.LoaderError as e:
        sys.exit("error: %s" % e)
    try:
        info = refresh_loader(args.loader_url)
    except fl.LoaderError as e:
        sys.exit("error: %s" % e)

    boot = open(BOOT, encoding="latin1").read()
    cfg = {
        "time_budget": 900, "executor": "Wave", "devirt": False,
        "spin": 60, "trace_globals": True, "serve": True,
    }
    d = tempfile.mkdtemp(prefix="fa2p_")
    hp = os.path.join(d, "harness.luau")
    src = harness.build_harness(boot, cfg, None)
    with open(hp, "w", encoding="latin-1", newline="\n") as f:
        f.write(src)
    print("[1] harness built (%.1f MB), bootstrapper %d B" % (len(src) / 1e6, len(boot)))

    proc = subprocess.Popen([LUAU], cwd=d, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    proc.stdin.write(b'__S = require("./harness")\n')
    proc.stdin.flush()
    time.sleep(10)                      # the ~3 MB harness module needs to compile
    try:
        while select.select([proc.stdout], [], [], 0.5)[0]:
            if not proc.stdout.read1(1 << 20):
                break
    except Exception:
        pass

    def repl(stmt, timeout=90, expect=None):
        proc.stdin.write(stmt.encode() + b"\n")
        proc.stdin.flush()
        end = (expect or harness.mark("ENVLOG-END")).encode()
        buf = b""
        t0 = time.time()
        while end not in buf:
            left = timeout - (time.time() - t0)
            if left <= 0:
                return None, buf.decode("latin-1", "replace")[-2000:]
            r, _, _ = select.select([proc.stdout], [], [], min(left, 5))
            if not r:
                continue
            chunk = proc.stdout.read1(1 << 20)
            if not chunk:
                return None, "process exited: " + buf.decode("latin-1", "replace")[-2000:]
            buf += chunk
        text = buf.decode("latin-1", "replace")
        if expect is not None:
            return text, None
        return text, None

    def drive(stmt, timeout):
        """Send one serve call; read the stream until the run suspends for a
        live hop (SUPERZREQ leak), finishes (ENVLOG-END), or times out."""
        proc.stdin.write(stmt.encode() + b"\n")
        proc.stdin.flush()
        buf = b""
        t0 = time.time()
        while True:
            left = timeout - (time.time() - t0)
            if left <= 0:
                return "timeout", buf.decode("latin-1", "replace")
            r, _, _ = select.select([proc.stdout], [], [], min(left, 2))
            if not r:
                continue
            chunk = proc.stdout.read1(1 << 20)
            if not chunk:
                return "dead", buf.decode("latin-1", "replace")
            buf += chunk
            text = buf.decode("latin-1", "replace")
            if B64RE.search(text):
                return "fetch", text
            if harness.mark("ENVLOG-END").encode() in buf:
                return "end", text

    planted = []

    def plant(url_u, body_u, headers_u, reqbody_u=None):
        # native-table plant via a require()d module (any size, no decoder);
        # reqbody pins the entry to the exact request body (the FlowAuth
        # payload endpoint reuses one URL for chunks 1/2)
        def esc(s):
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"') \
                .replace("\n", "\\n").replace("\r", "\\r") + '"'
        idx = len(planted) + 1001
        mod_p = os.path.join(d, "resp_%d.luau" % idx)
        hdr = "{" + ", ".join("[%s] = %s" % (esc(str(k)), esc(str(v)))
                              for k, v in list(headers_u.items())[:12]) + "}"
        rb = (esc(reqbody_u) + ", ") if reqbody_u is not None else "nil, "
        with open(mod_p, "w", encoding="latin-1") as f:
            f.write("return { url = %s, reqbody = %sbody = %s, headers = %s }\n"
                    % (esc(url_u), rb, esc(body_u), hdr))
        okp = None
        for attempt in range(3):
            okp, errp = repl('__S(require("./resp_%d"), "", "plant")' % idx,
                             120, expect="PLANT-")
            if okp is not None and "PLANT-OK" in okp:
                break
            print("    (plant retry %d)" % (attempt + 1))
        if okp is None or "PLANT-OK" not in okp:
            print("[!] plant failed:", (okp or errp or "")[-300:].strip())
            return False
        print("    planted as entry", idx - 1000)
        planted.append(url_u)
        return True

    mode, data = drive('__S("", "", "start")', 900)
    n = 0
    while mode == "fetch" and n < max_hops:
        n += 1
        for optleak in re.findall("\x01SUPERZREQOPTS\x01([A-Za-z0-9+/=]+)", data):
            try:
                print("        [opts-diag] " + base64.b64decode(
                    optleak + "=" * (-len(optleak) % 4)).decode("latin1", "replace")[:300])
            except Exception:
                pass
        leaks = B64RE.findall(data)
        lk = leaks[-1]
        try:
            meth, u, b = base64.b64decode(lk + "=" * (-len(lk) % 4)).decode("latin1").split("|", 2)
        except Exception as e:
            print("[!] leak decode failed:", e)
            break
        print("[hop %d] %s %s (%d B)" % (n, meth, u[:100], len(b)))
        if not u.startswith("http"):
            print("[!] non-HTTP request leaked (see opts-diag above); stopping")
            open(os.path.join(WORK, "proxy_leak.txt"), "w", encoding="latin1").write(data[-20000:])
            break
        if b:
            print("        body: %s" % b[:160])
        status, resp, hdrs = http(meth, u, b if meth == "POST" else None)
        print("        -> %d (%d B): %s" % (status, len(resp), resp[:130]))
        open(os.path.join(WORK, "hop_%02d_resp.txt" % n), "w", encoding="latin1").write(resp)
        if status != 200:
            print("[!] server rejected the hop; stopping")
            break
        if not plant(u, resp, hdrs, reqbody_u=(b if b else None)):
            break
        mode, data = drive('__S("", "", "resume")', 900)

    print("[2] loop finished after %d hop(s): mode=%s" % (n, mode))
    open(os.path.join(WORK, "two_phase_full.txt"), "w", encoding="latin1").write(data)
    st = re.search(r"-- run status: (.*)", data)
    print("    run status: %s" % (st.group(1)[:200] if st else "?"))
    for ln in [l for l in data.splitlines() if "loadstring() of" in l][:8]:
        print("    %s" % ln.strip()[:150])
    if mode not in ("end",):
        print("    tail: %s" % "\n".join(data.splitlines()[-12:])[:2000])
    body_m = re.search(re.escape(harness.mark("ENVLOG-BEGIN")) + r"\n(.*?)" +
                       re.escape(harness.mark("ENVLOG-END")), data, re.S)
    chunks = []
    if body_m:
        chunks, _ = harness.take_chunks(body_m.group(1))
    os.makedirs(os.path.join(WORK, "chunks"), exist_ok=True)
    for key, src_c in chunks:
        out = os.path.join(WORK, "chunks", "chunk_%s.luau" % key.replace("/", "_"))
        open(out, "w", encoding="latin1").write(src_c)
        print("[+] chunk %s -> %s (%d B)" % (key[:24], out, len(src_c)))
    if not chunks:
        print("    (no chunks captured)")
        print("\n".join(data.splitlines()[-25:])[:3000])
    proc.kill()

    payload = reassemble(info)
    if payload:
        print("[+] PAYLOAD (obfuscated source) -> %s (%d B)"
              % (payload, os.path.getsize(payload)))
        return 0
    return 0 if chunks else 1


if __name__ == "__main__":
    sys.exit(main())
