# FLOWAUTH — MASTER HANDOFF (every detail, one file)

> **Purpose**: a new session can resume ALL FlowAuth + Luraph v15 work from this file alone.
> Read top to bottom. The CONTINUOUS PROMPT at the end can be pasted verbatim into a fresh chat.
> Last updated: 2026-09-29 (session "devirt round-2: grind solved, full capture obtained").

---

## 0. TL;DR — current state in five lines

1. The chain behind `https://flowauth.net/v1/loaders/29f4f4b924aff467652814456286bb05.lua`
   is fully cracked end-to-end: loader → challenge → script → payload chunks → 713,630 B
   **Luraph Obfuscator v15** payload, captured and tracked in git.
2. The payload's anti-analysis **grind is SOLVED** (2026-09-29): 65 spin-head injections kill
   it cleanly at ~30 s with a 164 MB proto dump (**423,934 protos**, vs 64 before).
3. Round-1 devirt: 53 functions / 8.8 KB lifted (anti-tamper layer + VM scaffolding).
4. Remaining blocker (precisely diagnosed): the lifter's **env-slot function binding** —
   VM runtime helper closures stored in the env table (t10) have no proto/AST binding
   ("call of unknown VM function lf149"), plus the wrapper-factory case
   ("closure maker did not return the VM closure", devirt.py:740).
5. Standing user rules: **update `progress.md` every session**, deliverables go to
   `/home/z/my-project/download/`, no redundant repo work.

---

## 1. Credentials & endpoints

| Item | Value |
|---|---|
| Script key | (in session notes; redacted here — GitHub push protection blocks it) |
| GitHub token | (in `~/.git-credentials`; user `Aditya-lua`; redacted here — push protection) |
| Target loader URL | `https://flowauth.net/v1/loaders/29f4f4b924aff467652814456286bb05.lua` |
| Stage-2 host | `flowauth.net/assets/flowauth/sha256/<sha>/…`, fallback bare IP `37.187.136.187`, `?retry=8bb3d2ed31b00e82` |
| Stage-2 sha256 | `87c8738eb19de0ec5b9e2413a75845bbb740ca63c7ce3e216fd04d246ffdac7b` (content-addressed; equals URL-path hash) |

## 2. Repos (do NOT recreate — they exist)

| Path | GitHub | Branch | Contents |
|---|---|---|---|
| `/home/z/my-project/Deobfuscator-Luraph-V15` | `Aditya-lua/Deobfuscator-Luraph-V15` | `master` | Generic Luraph v15 devirt tool. Core: `core/` (devirt.py 3,638 L, harness.py, luasym.py, backend.py, codegen.py, structure.py…). Runtime: `runtime/envlog.luau` (6,118 L sandbox), `bin/luau` + `bin/luau-ast` (exec bits lost on fresh clone → `chmod +x`). |
| `/home/z/my-project/FlowAuth-Deobfuscator` | `Aditya-lua/FlowAuth-Deobfuscator` | `main` | All FlowAuth-specific tooling + tracked captures. **All FlowAuth work happens here.** |

Deleted long ago (do not recreate): GitHub repo `Aditya-lua/flowauth-devirt`, local `/home/z/my-project/flowauth-devirt/`.

## 3. FlowAuth v3 protocol (verified live, commit c86b451)

```
GET  loader (9,688 B, decimal-escaped URLs, multi-request global race)
     → handoff seeds pair e.g. "1411393296 626746395" (session-refreshed)
POST /v1/auth/challenge   → 200  protocol 3, credential_mode: loader
POST /v1/auth/script      → 200  runtime_keys.onyx-v1: 4e52a512…(64 hex)
POST /v1/auth/payload ×N  → 200  chunked (supports_chunked_payload), encoding lz4+base64
       2 chunks for this key: 524,313 B (token H0i524fZ…) + 260,733 B (token uLuWONEE…)
mode=end                  → loader loop finishes
```

- `credential_mode: loader`; request JSON includes `hash_algorithm: "sha256"`,
  `hwid: "6c1f8a20-4e2b-4c9d-9f3a-71b2d5e0a4c7"` (sandbox-stable), `launch_ticket: "v2:…"`,
  `proof` (sha256), `supports_lz4: true`.
- `payload_digest` is **session-keyed** (not plain sha256) — fresh vs tracked capture
  differ by only 277–289 watermark bytes (0.04%) → captures stay valid across sessions.
- Reassembled payload: **713,630 B** (server-confirmed `source_bytes`), = 76 B Luraph banner
  (`-- This file was protected using Luraph Obfuscator v15.0`) + LRM prelude
  (`LRM_ScriptName="Flow Loader"`) + Luraph v15 VM.
- `_bsdata0` handshake: loader publishes `{256 B blob, seed, seed}` to `getgenv()/_G/getfenv(runtime)`;
  stage-2 consumes it; session-bound, must be re-captured fresh per chain run.

## 4. Stage-2 bootstrapper (586,282 B)

- File `flowauth_crack/work/runtime_marbeg.lua` (tracked content, gitignored path — see §7).
- `-- This file was protected using Luraph Obfuscator v15.0` header (https-stripped).
- Inside sandbox it does the auth flow; its own in-sandbox lz4 step fails by design
  (`warn("[FlowAuth] FlowAuth: payload could not be decompressed")`) — python-side
  `reassemble_payload.py` bypasses (chunks are lz4+base64; decoded+concatenated offline:
  393,216 + 195,530 → 713,630 B... precisely: decoded chunk sizes 393,216 + 320,414).

## 5. File map — FlowAuth-Deobfuscator

```
flowauth_capture/                (TRACKED in git)
  payload_source.lua   713,630 B  raw Luraph v15 payload = THE CODE BEHIND THE URL
  payload_devirt.lua   713,706 B  banner + payload (lift input)
  payload_lift.lua       8,837 B  round-1 devirt (53 fns, antitamper layer)
  capture_protos.json.gz   OLD 64-proto capture (obsoleted 2026-09-29 by grind fix)
  hop_*.txt                      live hop responses
flowauth_crack/
  flowauth_two_phase.py          full chain driver (--loader-url, default = our URL)
  gen_boot.py                    bootstrapper builder (needs PYTHONPATH=main repo/core)
  reassemble_payload.py          chunk decode/concat (has fresh-clone banner fallback, commit 2d56e3d)
  patch_envlog.py                envlog patcher for the chain run (sha256/base64/json shims,
                                 canned responses, _bsdata0, SUPERZ leak markers)
  sha256.luau base64.luau json.luau   pure-Luau impls
  work/                          (gitignored) runtime_marbeg.lua, bootstrapper.lua,
                                 payload_source/devirt.lua, chunks, logs, NEW captures
devirt_full.py                   NEW 2026-09-29: full-pipeline devirt with grind kill
lift_new_capture.py              NEW: staged lift from the new 164 MB dump
lift_flowauth_payload.py         OLD single static pass (kept for reference)
capture_v3.py capture_v4.py capture_fresh_protos.py   earlier (failed) capture attempts
probe_flowauth_devirt.py probe_hot_proto.py probe_progress.py   probes
progress.md                      PER-SESSION STATE LOG — UPDATE IT EVERY SESSION
```

## 6. THE GRIND — root cause chain and the fix (most important section)

**Symptom**: running the payload in the envlog sandbox dies by OOM SIGKILL (~80 MB/s
allocation, 3.6 GB in <60 s), zero output, no abort, no dump. All 2026-09-28 capture
attempts (`capture_v3/v4`, /tmp/fresh_raw3/4.txt) produced 0 bytes because of it.

**Eliminated causes (tested)**:
- Statement time-budget: never fires (grind emits no statements).
- Spin watchdog (`driver.patch_spin`): **its regex matches 0 loop heads in this build** —
  this payload's loops are `while true do if not(x<=15)then…` shaped, the regex expects
  `while true do <locals>=<array>;`. Watchdog was completely dead.
- Entry-hook STALL_KILL: injected, but this build has ONE entry hook (the giant dispatch
  function), it fires ONCE at entry (`__ENT.n=1`, `1 % 128 ≠ 0` → check skipped, never re-runs).
- Maker-hook STALL_KILL: fires, but `error()` is a STRING error — the script's tamper
  routine **pcalls and swallows it** (envlog deliberately passes the REAL pcall through:
  `E.pcall = R.pcall`, devirt fingerprints the stack).
- envlog `newP()` proxy-flood abort: grind allocates raw Lua objects, not proxies → never fires.
- `ulimit -v` (RLIMIT_AS 2.9 GB): prevents OOM but the grind GC-thrashes forever at ~505 MB
  (garbage is unreachable; Luau GC keeps it alive-able) — no clean exit.

**Actual mechanism**: after the VM root enters the tamper-check function (pid 3), a
Luraph tamper-response handler loops internally INSIDE ONE VM instruction (dispatch head
never re-executes), allocating unreachable garbage forever.

**THE FIX** (in `devirt_full.py`): inject `__SPIN` counting into EVERY `while true do`
head of the payload source:

```python
SPIN_HEAD = ("if __SPIN then __SPIN.n=__SPIN.n+1;"
             "if __SPIN.n>=__SPIN.step then __SPIN.f()end;end;")
re.subn(r"\bwhile true do ", lambda m: m.group(0) + SPIN_HEAD, src)   # 65 heads
```

`__SPIN.f()` (envlog) counts idle checks (no statement + no new proxy = idle); after
`CFG.spin` (24) consecutive idle checks it raises the clean ABORT → envlog wrap-up →
trace + PROTOS dump land. Result: clean exit at t≈30 s, rc=0,
`-- run status: aborted: endless loop in the script's own code (no environment access)`.

**Yield** (2026-09-29): 164,039,519 B output → `payload_full.protos.json`:
**423,934 protos / 428,962 tables / 20 entered pids / 695 distinct lf function values**.
Trace shows REAL payload code executed: `Instance.new("UIScale"/"UISizeConstraint"/"UIPadding")`,
`TextButton2`, `Vector2.new(25,1)` — the Flow Loader UI builder ran.

## 7. Fresh-clone bootstrap (exact commands)

```bash
cd /home/z/my-project/FlowAuth-Deobfuscator
# 0. exec bits (lost on clone):
chmod +x /home/z/my-project/Deobfuscator-Luraph-V15/bin/luau*
# 1. stage-2 runtime (content-addressed, session-independent) →
#    flowauth_crack/work/runtime_marbeg.lua (586,282 B, verify sha256 87c8738e…)
# 2. bootstrapper:
PYTHONPATH=/home/z/my-project/Deobfuscator-Luraph-V15/core python3 flowauth_crack/gen_boot.py
# 3. full chain (network; default --loader-url is our URL):
python3 flowauth_crack/flowauth_two_phase.py 24 \
  --loader-url https://flowauth.net/v1/loaders/29f4f4b924aff467652814456286bb05.lua
# 4. reassemble + old-style lift:
python3 flowauth_crack/reassemble_payload.py && python3 lift_flowauth_payload.py
# 5. NEW: full-pipeline devirt with grind kill (this is the one that works):
python3 devirt_full.py                    # budget=400 rounds=200 kill=18s
python3 lift_new_capture.py               # staged lift from work/payload_full.protos.json.gz
```

Note: `work/` is gitignored; if missing, restore `runtime_marbeg.lua` by fetching the
stage-2 URL and `payload_devirt.lua` = tracked `flowauth_capture/payload_devirt.lua`.

## 8. Devirtualization — precise remaining blockers

**Round-1 result** (old 64-proto capture): 53 fns / 8,837 B — anti-tamper env table
(`tbl = {[42]=islclosure, [282]="delay", [569]="AnchorPoint", [618]="RunService", …}` +
partial fused handlers) with 72 unlifted blocks of three kinds:
`index nil @272,…` (missing constant slot), `call of unknown VM function lf141/lf155`
(unbound helper), `arith on None None`.

**New-capture status** (423K protos): lift reaches stepper init and fails at
`call of unknown VM function lf149` — SAME blocker class, now precisely mapped:

1. **Env-slot binding gap.** The VM env/slot table (dump table **t10**, 61 slots:
   builtins at 1–16ish, lf closures at 3,29,30,34,40–43,46,48–58,59,60) is referenced by
   EVERY cap as field `A`. Its lf closures are **VM runtime helpers defined in the visible
   prelude** (not virtualized protos!) but stored into t10 dynamically — no
   `A[49] = function` static assignment exists (verified: `ctor_assignments` has 19 entries,
   A-keys 3,42,43,46,52–57,59,60 only; no big table constructors; no `A[49]` write in AST).
   → devirt.py's binding loop (line 2837–2863) only scans **cap fields** for OpaqueFn,
   never table contents → t10 slots stay unbound → `call_symbolic` raises
   "call of unknown VM function lfN" (line 1615).
2. **Wrapper factory.** `ProtoLifter.__init__` calls the factory symbolically and requires
   the VM closure back (line 736–740); this build's factory returns a wrapper
   → "closure maker did not return the VM closure" (seen in round-1 output at [668]).
3. **20 entered pids → caps**: entered pid tables map to caps at **tid+1**
   (pid 1→t339806 root, pid 3→t8418, pid 4→t63, pid 5→t98246, pid 6→t380123, pid 7→t616,
   pid 8→t8119, pid 9→t8026, pid 10→t226575, pid 11→t166370, pid 12→t1211, pid 13→t7624,
   pid 14→t1447, pid 15→t17860, pid 16→t2815, pid 17→t32952, pid 18→t48487, pid 19→t66631,
   pid 20→t21, pid 21→t49). These are the REAL executed functions (UI builders etc.).
4. **Next-session plan**:
   a. Extend devirt.py binding: after the cap-field pass, walk cap-field **tables**
      (esp. field A) and bind OpaqueFn slots to AST nodes — resolve how t10 is filled
      (loop with computed keys? capture the fill by tracing `A[k]=v` statements in the
      maker's symbolic exec — `ProtoLifter` already runs the maker symbolically; the
      puts into A during that exec give (slot → function node) pairs directly!).
   b. Handle the wrapper factory: if symbolic factory returns a non-LuaFunc wrapper,
      follow `wrapper → inner VM closure` (the wrapper's body typically calls the real
      closure once; bind through it).
   c. Then `lift_new_capture.py` (or the full `devirt_full.py` multi-round + live fetch)
      should lift the 20 entered protos → the payload's real logic.
   d. Keep KILL_AFTER/spin-head injection for ALL future runs (env-var KILL_AFTER).

## 9. Sandbox notes (envlog quirks that cost hours — read before debugging)

- luau stdout is block-buffered; a killed process loses EVERYTHING (traces print at
  wrap-up). Use `DEVIRT_TRACE_DEBUG=1 python3 devirt_full.py` (streams to file, memory watch).
- Background processes are reaped between tool calls in this environment → run
  long phases in FOREGROUND with `timeout 570`, split into stages.
- Machine: 3.9 GB RAM total. Grind OOMs the box (kills luau mid-run). Python Program
  build on the 164 MB dump ≈ 40 s and ~1–2 GB — fine.
- `E.pcall = R.pcall` is REAL pcall (Luraph fingerprints it) — the script can swallow
  any Lua error; only envlog's `coroutine.yield(ABORT)` escape (checkBudget, ≥2 hits)
  is uncatchable, and it needs statement/proxy "opportunities".
- Heartbeat: `run_once` pads 16 KB per HB to push the pipe buffer — kills show as rc=-9
  with 0 B output when nothing flushes.
- Path2D: "11 Path2D answers computed by the offline engine model" is normal.

## 10. Deliverables (also mirrored to /home/z/my-project/download/)

- `flowauth_payload_source.lua` — 713,630 B raw Luraph v15 payload (the code behind the URL)
- `flowauth_payload_lift.lua` — round-1 devirt (53 fns)
- `LuraphV15-Devirtualized.zip`, `README.md`, `progress.md` — earlier session artifacts
- NEW this session: `flowauth_crack/work/payload_full.protos.json.gz` (7.9 MB gz),
  `payload_full.trace.txt` (164 MB), `devirt_full.py`, `lift_new_capture.py`

---

## 11. CONTINUOUS PROMPT — paste this into a fresh session

```
You are continuing a long-running reverse-engineering project. Read these first,
in this order, before doing anything else:
1. /home/z/my-project/FlowAuth-Deobfuscator/FLOWAUTH_HANDOFF.md  (master handoff — everything)
2. /home/z/my-project/FlowAuth-Deobfuscator/progress.md         (per-session state log)
3. /home/z/my-project/worklog.md                                (multi-agent work log)

Standing rules:
- Update /home/z/my-project/FlowAuth-Deobfuscator/progress.md EVERY session (latest entry
  first) so context is never lost. No redundant repo work — the repos already exist:
  /home/z/my-project/Deobfuscator-Luraph-V15 (generic Luraph v15 devirt tool, branch master)
  and /home/z/my-project/FlowAuth-Deobfuscator (all FlowAuth work, branch main, push to
  origin with the token already in ~/.git-credentials).
- User-facing deliverables are copied to /home/z/my-project/download/.
- Run long phases in FOREGROUND (timeout 570 per call) — background processes get reaped.
- This session: DEVIRTUALIZING LURAPH V15 SCRIPTS ONLY.

Current mission: finish devirtualizing the FlowAuth payload (the Luraph v15 code behind
https://flowauth.net/v1/loaders/29f4f4b924aff467652814456286bb05.lua). The anti-analysis
grind is already SOLVED (spin-head injection in devirt_full.py — read FLOWAUTH_HANDOFF.md
§6 before touching anything). The new capture is at
flowauth_crack/work/payload_full.protos.json.gz (423,934 protos; 20 entered pids map to
caps at tid+1 — see §8). The remaining blockers are precisely diagnosed in §8:
(a) bind the env-slot helper closures (table t10, cap field A) to their AST nodes — the
maker's symbolic exec (ProtoLifter.__init__ runs vm.maker with ProtoLifter as the
interpreter) puts functions into A; record those puts as (slot → node) bindings and apply
them to the OpaqueFn values before walking; (b) handle the wrapper factory
(devirt.py:740 "closure maker did not return the VM closure"). Then lift the 20 entered
protos (t339806 root, t8418, t63, t98246, t380123, t616, t8119, t8026, t226575, t166370,
t1211, t7624, t1447, t17860, t2815, t32952, t48487, t66631, t21, t49) with
lift_new_capture.py, and deliver the full readable source to /home/z/my-project/download/.
Keep KILL_AFTER/spin-head injection for every sandbox run. Update progress.md, commit and
push FlowAuth-Deobfuscator (branch main) at the end, and append to worklog.md.
```
