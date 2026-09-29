# progress.md — running state log

> Updated every session so context is never lost. Latest entry first.

## 2026-09-29 — fresh capture on request loader `29f4f4b9…` (READY status confirmed)

**Status: pipeline READY for new script URLs.** Ran `flowauth_two_phase.py` live against
`https://flowauth.net/v1/loaders/29f4f4b924aff467652814456286bb05.lua` from a fresh clone
state. Full chain succeeded in ONE luau process:

1. `[0]` fresh loader fetched: 9,688 B, handoff seeds `1411393296 626746395` (session-refreshed)
2. envlog sandbox patched (306,573 B), harness built (1.2 MB), bootstrapper 586,598 B
3. hop 1 → `POST /v1/auth/challenge` → **200** (protocol 3, `credential_mode: loader`)
4. hop 2 → `POST /v1/auth/script` → **200** (`runtime_keys.onyx-v1: 4e52a512…`)
5. hop 3 → `POST /v1/auth/payload` → **200** (524,313 B chunk, token `H0i524fZ…`)
6. hop 4 → `POST /v1/auth/payload` → **200** (260,733 B chunk, token `uLuWONEE…`)
7. loop finished mode=end; runtime's own in-sandbox lz4 step errored
   (`FlowAuth: payload could not be decompressed`) — expected; python-side reassembly bypasses it
8. `reassemble_payload.py`: chunks 393,216 + 195,530 → **713,630 B payload**
   (server-confirmed size), LRM prelude head (`LRM_ScriptName="Flow Loader"`)
9. **fresh vs tracked payload: same 713,630 B, 289 bytes differ (0.040%)** — per-session
   watermarks only, `payload_digest` is session-keyed (not plain sha256) — captures stay valid
10. lift on fresh payload: **53 functions / 8,837 B** → `flowauth_capture/payload_lift.lua`

**Fixed this session** (fresh-clone bug): `reassemble_payload.py` derived an empty 76-byte
Luraph banner header when `work/payload_devirt.lua` didn't exist yet (work/ is gitignored),
producing a devirt input the lifter parsed as 0 functions. Now falls back to the tracked
`flowauth_capture/payload_devirt.lua` header. Committed.

**Fresh-clone bootstrap** (what was needed from empty `work/`):
```bash
# 1. stage-2 runtime (session-independent, sha256 content-addressed):
python3 tools/fetch_stage2.py   # or any curl of the /assets/flowauth/sha256/<hash>/… URL
#    → put it at flowauth_crack/work/runtime_marbeg.lua
# 2. generate bootstrapper (needs main repo core on PYTHONPATH):
PYTHONPATH=/home/z/my-project/Deobfuscator-Luraph-V15/core python3 gen_boot.py
# 3. run the chain (default loader-url is the 29f4f4b9… one):
python3 flowauth_two_phase.py 24 --loader-url https://flowauth.net/v1/loaders/<md5>.lua
# 4. reassemble + lift:
python3 reassemble_payload.py && python3 lift_flowauth_payload.py
```

**Housekeeping:** a stray duplicate repo `Aditya-lua/flowauth-devirt` was created earlier
this session by mistake (context loss) — the real standalone repo is THIS one
(`FlowAuth-Deobfuscator`, split in commit `70a6b45` of the main repo). Delete
`flowauth-devirt` if the API couldn't.

**Ready to accept:** any `flowauth.net/v1/loaders/<md5>.lua` URL — chain + capture + lift
run unattended. Next devirt wave (unchanged): junk-guard walk errors, unbound helpers
(`lf141`/`lf155`), vararg rendering, lazy constants via live-fetch loop.

---

## 2026-09-28 — session-independent chain + parameterized loader (commit 7210e6f)

- Chain proven end-to-end twice in separate sessions; only 277 watermark bytes differ
  between sessions → `payload_digest` is session-keyed, captures valid across sessions.
- `flowauth_two_phase.py` takes `--loader-url` (any `/v1/loaders/<md5>.lua`) — ready for
  new scripts.
- Robust reassembly committed.

## 2026-09-28 — FlowAuth split into its own repo (commit 70a6b45, da76083)

- All FlowAuth tooling moved out of Deobfuscator-Luraph-V15 → **FlowAuth-Deobfuscator**.
- Main repo keeps: sandbox harness (`runtime/envlog.luau`), `bin/luau`, generic devirt core.
- Tracked capture: `flowauth_capture/` (payload_source.lua 713,630 B, protos 64 / 4,986
  tables, hop responses, round-1 lift 53 fns).
