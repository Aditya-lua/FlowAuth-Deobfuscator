#!/usr/bin/env python3
"""Round-2+ FlowAuth payload devirtualization via the main repo's full pipeline.

driver.run(job) on the captured Luraph v15 payload: entry hooks -> trace run ->
loadstring'd chunk instrumentation -> anti-tamper trap skipping -> live-harness
constant rounds -> multi-round lift.

The payload has an anti-analysis grind: after the root enters its tamper-check
proto, execution loops forever allocating (proxies pinned by envlog's BYID +
closures pinned by __PA) at ~80 MB/s -> OOM SIGKILL in <60s, zero output. The
spin watchdog cannot catch it (each proxy access counts as progress) and the
statement budget cannot (no statements). Fix: a wall-clock abort injected at
two allocation points envlog itself owns:
  1. runtime newP() (every proxy allocation) -> R.error(ABORT, 0), a clean
     budget abort: envlog wraps up, dumps trace + PROTOS;
  2. the driver's maker/entry hooks (__PA.n / __ENT.n counters) -> error().

Usage: python3 devirt_full.py [budget] [rounds]
Env:   KILL_AFTER (default 18s), DEOB_NO_SERVE=1, DEVIRT_FULL_ROUNDS=1,
       HARNESS_TIMEOUT (default 240s), MAX_RUNS (default 4)
"""
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = "/home/z/my-project/Deobfuscator-Luraph-V15"
sys.path.insert(0, os.path.join(MAIN, "core"))

import harness  # noqa: E402
from obfuscators.base import Job  # noqa: E402
from obfuscators.luraph_v15 import driver as ldrv  # noqa: E402

SRC = os.path.join(HERE, "flowauth_crack", "work", "payload_devirt.lua")
OUT_BASE = os.path.join(HERE, "flowauth_crack", "work", "payload_full")

BUDGET = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("TIME_BUDGET", "400"))
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("DEVIRT_ROUNDS", "200"))
TIMEOUT = int(os.environ.get("HARNESS_TIMEOUT", "240"))
MAX_RUNS = int(os.environ.get("MAX_RUNS", "4"))
KILL_AFTER = float(os.environ.get("KILL_AFTER", "18"))

HOOK_CHECK = ("if __ENT.n % 128 == 0 and __SZ_CLK and __SZ_CLK() - __SZ_T0 > __SZ_KILL "
              "then error('STALL_KILL in hook at ent ' .. __ENT.n, 0) end;")

MAKER_CHECK = ("if __PA.n % 256 == 0 and __SZ_CLK and __SZ_CLK() - __SZ_T0 > __SZ_KILL "
               "then error('STALL_KILL in maker at ' .. __PA.n, 0) end;")

PRELUDE = ("local E = env "
           "E.__SZ_CLK = E.os.clock "
           "E.__SZ_T0 = E.os.clock() "
           "E.__SZ_KILL = %f") % KILL_AFTER

_orig_patch = ldrv.patch_entries

SPIN_HEAD = ("if __SPIN then __SPIN.n=__SPIN.n+1;"
             "if __SPIN.n>=__SPIN.step then __SPIN.f()end;end;")


def _patch_with_kill(source, path):
    out = _orig_patch(source, path)
    out, n1 = re.subn(
        r"(__ENT\.n=__ENT\.n\+1;__ENT\[__ENT\.n%64\]=__PID\[[^\]]*\];)",
        lambda m: m.group(1) + " " + HOOK_CHECK,
        out,
    )
    out, n2 = re.subn(
        r"(__PA\.n=__PA\.n\+1;)",
        lambda m: m.group(1) + MAKER_CHECK,
        out,
    )
    # this build's loop heads don't match driver.patch_spin's regex ("while
    # true do if not(x<=15)then..."), which left the spin watchdog dead and
    # the anti-tamper grind unkillable: inject at EVERY while-true head
    out, n3 = re.subn(
        r"\bwhile true do ",
        lambda m: m.group(0) + SPIN_HEAD,
        out,
    )
    print("[*] STALL_KILL: %d entry hooks, %d maker hooks, %d spin heads (kill after %.0fs)"
          % (n1, n2, n3, KILL_AFTER), file=sys.stderr)
    return out


ldrv.patch_entries = _patch_with_kill


def install_patched_runtime():
    """envlog copy with the newP wall-clock abort; harness.RUNTIME_DIR -> it."""
    tmp = tempfile.mkdtemp(prefix="envlog_grindkill_")
    src_dir = harness.RUNTIME_DIR
    for nm in os.listdir(src_dir):
        shutil.copy(os.path.join(src_dir, nm), os.path.join(tmp, nm))
    p = os.path.join(tmp, "envlog.luau")
    with open(p, encoding="utf-8") as f:
        rt = f.read()
    old = ("local function newP(info)\n"
           "        nextId += 1\n")
    new = ("local function newP(info)\n"
           "        nextId += 1\n"
           "        if nextId %% 4096 == 0 and R.clock() - START > %f then\n"
           "                ABORT_REASON = \"STALL_KILL: proxy flood grind (newP), %.0fs wall\"\n"
           "                R.error(ABORT, 0)\n"
           "        end\n" % (KILL_AFTER, KILL_AFTER))
    assert old in rt, "newP anchor not found in envlog.luau"
    rt = rt.replace(old, new, 1)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(rt)
    harness.RUNTIME_DIR = tmp
    print("[*] envlog grind-kill installed at %s" % tmp, file=sys.stderr)


class Args:
    budget = BUDGET
    timeout = TIMEOUT
    devirt_rounds = ROUNDS
    executor = "Wave"
    studio = False
    raw = os.path.join(HERE, "flowauth_crack", "work", "payload_full.raw.txt")
    strings = False
    no_fold = False
    no_hooks = False
    no_devirt = False
    max_runs = MAX_RUNS
    input_text = None
    port = None
    cfg = ["prelude=" + PRELUDE]
    keep_harness = False

    def __getattr__(self, k):
        return False


def trace_debug():
    """Manual single harness run with file-logged output + memory watch.
    Devtool for the grind: shows exactly what happens before the kill."""
    import subprocess
    d = tempfile.mkdtemp(prefix="fa_gk_")
    cfg = {"time_budget": BUDGET, "executor": "Wave", "devirt": True, "spin": 24,
           "prelude": PRELUDE}
    with open(SRC, "r", encoding="latin-1") as f:
        source = f.read()
    patched = _patch_with_kill(source, SRC)
    h = harness.build_harness(patched, cfg, None)
    hp = os.path.join(d, "harness.luau")
    with open(hp, "w", encoding="latin-1", newline="") as f:
        f.write(h)
    print("[*] debug harness at %s (%d B)" % (hp, len(h)), file=sys.stderr)
    t0 = time.time()
    outp = os.path.join(d, "out.txt")
    logf = open(outp, "wb")
    proc = subprocess.Popen([harness.find_luau(), hp], cwd=d, stdout=logf,
                            stderr=subprocess.STDOUT)
    while proc.poll() is None and time.time() - t0 < 360:
        time.sleep(5)
        m = os.popen("free -m | head -2 | tail -1").read().split()
        print("[*] t=%4.0fs rc=%s used=%sMB out=%dB"
              % (time.time() - t0, proc.poll(), m[2] if m else "?",
                 os.path.getsize(outp)), file=sys.stderr)
    logf.close()
    print("[*] ended rc=%s after %.0fs, %d B output"
          % (proc.returncode, time.time() - t0, os.path.getsize(outp)), file=sys.stderr)
    data = open(outp, "rb").read()
    with open(os.path.join(HERE, "flowauth_crack", "work", "payload_full.raw.txt"), "wb") as f:
        f.write(data)
    m = re.search(re.escape(harness.mark("ENVLOG-BEGIN")) + r"\n(.*?)" +
                  re.escape(harness.mark("ENVLOG-END")), data.decode("utf-8", "replace"), re.S)
    if not m:
        print("[!] no ENVLOG markers; tail: %r" % data[-300:], file=sys.stderr)
        return
    body = m.group(1)
    with open(os.path.join(HERE, "flowauth_crack", "work", "payload_full.trace.txt"), "w",
              encoding="utf-8", errors="replace") as f:
        f.write(body)
    protos = re.search(re.escape(harness.mark("PROTOS ")) + r"([^\n]*)\n", body)
    if protos:
        js = protos.group(1)
        with open(os.path.join(HERE, "flowauth_crack", "work", "payload_full.protos.json"), "w",
                  encoding="utf-8") as f:
            f.write(js)
        print("[*] protos saved: %d B" % len(js), file=sys.stderr)
    lines = [l for l in body.split("\n") if l.strip()]
    print("[*] trace lines: %d; last 20:" % len(lines), file=sys.stderr)
    for l in lines[-20:]:
        print("   " + l[:170], file=sys.stderr)


def main():
    t0 = time.time()
    install_patched_runtime()
    if os.environ.get("DEVIRT_TRACE_DEBUG"):
        trace_debug()
        return
    with open(SRC, "r", encoding="latin-1") as f:
        source = f.read()
    args = Args()
    job = Job(SRC, source, args, OUT_BASE + ".deobf.luau", False, "Luraph v15")
    job.source_path = SRC
    job.credit_header = lambda: ""

    print("[*] full pipeline: budget=%ss rounds=%d timeout=%ss max_runs=%d kill=%.0fs"
          % (BUDGET, ROUNDS, TIMEOUT, MAX_RUNS, KILL_AFTER), file=sys.stderr)
    result = ldrv.run(job)
    print("[*] done in %.0fs -> %s" % (time.time() - t0, result), file=sys.stderr)
    if result and os.path.exists(result):
        with open(result, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        print("[*] output: %d bytes, %d lines" % (len(text), text.count("\n") + 1))
        print("[*] (nil)( calls: %d" % text.count("(nil)("))


if __name__ == "__main__":
    main()
