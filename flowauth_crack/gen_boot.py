#!/usr/bin/env python3
"""Generate work/bootstrapper.lua: embed a verified FlowAuth runtime and run it
exactly like `loadstring(game:HttpGet(...))()` would (credential = nil).
The _bsdata0 handoff is preseeded by patch_envlog.py, so the loader itself
never needs to run (its game:HttpGet transport returns a proxy in-sandbox).

By default it wraps an existing work/runtime_marbeg.lua. Pass --loader-url to
fetch + verify a fresh runtime for any loader first (flowauth_two_phase.py does
this automatically; this stays as a standalone helper).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flowauth_loader as fl  # noqa: E402

RUNTIME = os.path.join(HERE, "work", "runtime_marbeg.lua")
OUT = os.path.join(HERE, "work", "bootstrapper.lua")


def main():
    ap = argparse.ArgumentParser(description="Build work/bootstrapper.lua from a verified runtime")
    ap.add_argument("--repo", default=None,
                    help="Deobfuscator-Luraph-V15 repo (else FLOWAUTH_REPO / auto-discover)")
    ap.add_argument("--loader-url", default=None,
                    help="fetch + verify the runtime for this loader URL instead of using work/runtime_marbeg.lua")
    args = ap.parse_args()

    repo = fl.find_repo(args.repo)
    sys.path.insert(0, os.path.join(repo, "core"))
    from harness import long_string  # noqa: E402

    os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    if args.loader_url:
        info = fl.parse_loader(fl.fetch_loader(args.loader_url), args.loader_url)
        runtime, _ = fl.fetch_runtime(info)
        with open(RUNTIME, "wb") as f:
            f.write(runtime)
        src = runtime.decode("latin1")
    else:
        src = open(RUNTIME, encoding="latin1").read()

    boot = fl.build_bootstrapper(src, long_string)
    with open(OUT, "w", encoding="latin1", newline="\n") as f:
        f.write(boot)
    print("wrote", OUT, len(boot), "bytes (runtime", len(src), "bytes)")


if __name__ == "__main__":
    try:
        main()
    except fl.LoaderError as e:
        sys.exit("error: %s" % e)
