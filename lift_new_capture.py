#!/usr/bin/env python3
"""Lift the FlowAuth payload from the NEW (post-grind-fix) capture.

Standalone lift driver: builds the Program once, then lifts the payload VM
root(s) with error-tolerant output (one failing child doesn't kill the run).
Writes payload_full.devirt.luau + stats.

Env: DUMP (default work/payload_full.protos.json.gz), SRC, OUT.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = "/home/z/my-project/Deobfuscator-Luraph-V15"
sys.path.insert(0, os.path.join(MAIN, "core"))

from obfuscators.luraph_v15 import devirt  # noqa: E402

SRC = os.environ.get("SRC", os.path.join(HERE, "flowauth_crack", "work", "payload_devirt.lua"))
DUMP = os.environ.get("DUMP", os.path.join(HERE, "flowauth_crack", "work", "payload_full.protos.json.gz"))
OUT = os.environ.get("OUT", os.path.join(HERE, "flowauth_crack", "work", "payload_full.devirt.luau"))


def main():
    t0 = time.time()
    prog = devirt.Program(SRC, DUMP)
    prog.requests = set()
    print("[*] Program built %.0fs; vms: %s" % (time.time() - t0, list(prog.vms)), file=sys.stderr)

    vms, payload = devirt._vm_roots(prog)
    print("[*] roots: %s (payload=%r)" % ([(t.decode("latin-1"), len(l)) for t, l in vms], payload),
          file=sys.stderr)

    fl = devirt.FunctionLifter(prog)
    out = []
    for tag, lst in vms:
        _, pid, cap = lst[0]
        where = tag.decode("latin-1")
        try:
            vm = prog.vm_of(cap)
        except devirt.Unsupported as ex:
            out.append("-- VM %s: root #%s not lifted: %s" % (where, pid, ex))
            continue
        proto = vm.proto_of(cap)
        vmobj = vm.vmobj_of(cap)
        t1 = time.time()
        try:
            lines = fl.lift(vm, vmobj, proto, devirt.UpList(), {}, 0)
        except devirt.Unsupported as ex:
            print("[!] root %s lift failed: %s" % (pid, ex), file=sys.stderr)
            out.append("-- root %s failed: %s" % (pid, ex))
            continue
        out.append("-- VM %s root #%s (%d caps, %.0fs)" % (where, pid, len(lst), time.time() - t1))
        out += lines
    text = devirt.backend.polish("\n".join(out))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("[*] stats: %s" % fl.stats, file=sys.stderr)
    print("[*] requests: %d" % len(prog.requests), file=sys.stderr)
    print("[*] wrote %s (%d bytes) in %.0fs" % (OUT, len(text), time.time() - t0), file=sys.stderr)


if __name__ == "__main__":
    devirt.run_big_stack(main)
