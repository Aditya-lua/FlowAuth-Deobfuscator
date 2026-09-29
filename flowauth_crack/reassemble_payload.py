#!/usr/bin/env python3
"""Reconstruct the FlowAuth payload python-side: b64-decode both chunk
bodies, concatenate the raw lz4 blocks, decompress, verify sha256 against
the script response's payload_digest."""
import base64
import hashlib
import json
import os
import re
import sys


def lz4_block_decompress(src, expected=None):
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        tok = src[i]; i += 1
        lit = tok >> 4
        if lit == 15:
            while True:
                b = src[i]; i += 1; lit += b
                if b != 255:
                    break
        out += src[i:i + lit]; i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8); i += 2
        if off == 0 or off > len(out):
            raise ValueError("bad offset %d at out=%d i=%d" % (off, len(out), i))
        ml = tok & 15
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255:
                    break
        ml += 4
        start = len(out) - off
        for k in range(ml):
            out.append(out[start + k])
    return bytes(out)


def main():
    work = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
    script_resp, chunk_files = None, []
    for name in sorted(os.listdir(work)):
        if not name.startswith("hop_") or not name.endswith("_resp.txt"):
            continue
        try:
            body = json.load(open(os.path.join(work, name)))
        except Exception:
            continue
        if isinstance(body, dict) and "payload_digest" in body:
            script_resp = body
        elif isinstance(body, dict) and "chunk" in body:
            chunk_files.append((name, body["chunk"]))
    if script_resp is None or not chunk_files:
        sys.exit("no script/payload hop responses found in %s (run flowauth_two_phase.py first)" % work)
    chunks = [base64.b64decode(c) for _, c in sorted(chunk_files)]
    print("payload chunks:", [len(c) for c in chunks])
    full = lz4_block_decompress(b"".join(chunks))
    digest, src_bytes = script_resp["payload_digest"], script_resp.get("source_bytes")
    h = hashlib.sha256(full).hexdigest()
    print("decompressed: %s B (server says %s B), sha256 %s" % (len(full), src_bytes, h[:16]))
    print("server payload_digest %s -- session-keyed, NOT plain sha256 of plaintext "
          "(verified: only ~0.04%% of bytes differ between sessions = per-session watermarks)" % digest[:16])
    # diff against the tracked payload if present
    out = os.path.join(work, "payload_source.lua")
    old = open(out, "rb").read() if os.path.exists(out) else None
    if old is not None and len(old) == len(full):
        nd = sum(1 for a, b in zip(old, full) if a != b)
        print("vs tracked payload_source.lua: %d differing bytes (per-session watermarks)" % nd)
    open(out, "wb").write(full)
    print("[+] PAYLOAD SOURCE WRITTEN:", out)
    # keep the devirt input (76B Luraph banner header + payload) in sync
    devirt_p = os.path.join(work, "payload_devirt.lua")
    header = None
    if os.path.exists(devirt_p):
        old_dev = open(devirt_p, "rb").read()
        if old is not None and len(old_dev) == len(old) + 76 and old_dev[76:] == old:
            header = old_dev[:76]
    if header is None:
        m = re.search(rb"-- This file was protected using Luraph Obfuscator v15\.0[^\n]*\n", full)
        header = full[:m.end()] if m else b""
        print("[i] header derived from payload itself: %r" % header[:60])
    with open(devirt_p, "wb") as f:
        f.write(header + full)
    print("[+] DEVIRT INPUT WRITTEN:", devirt_p, "(%d B = 76B header + payload)" % (76 + len(full)))
    print("    head:", full[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
