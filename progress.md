# progress.md — running state log

> Updated every session so context is never lost. Latest entry first.

## 2026-09-29 (evenest) — RaceforEggs (v14.9) direct devirt: 119/119 protos lifted

Session scope (user): "this session should be only devirtualizing luraph v15 scripts" +
"Only give me lurapi v15 code behind it". Ran the user's RaceforEggs URL through the
DIRECT Luraph pipeline (not the FlowAuth chain).

**Deliverable:** `/home/z/my-project/download/RaceforEggs.devirtualized.lua`
(9.5k lines, all 119 captured protos lifted, 0 lift failures, 17 residual error
markers = paths whose constants the sandbox trace never decoded).

**v14.9 lifter fixes landed in Deobfuscator-Luraph-V15 this session:**
1. `value_of`: hash-keyed VM tables now render as table constructors (`table_ctor`)
   instead of raising "storing a non-empty VM table" (config tables `{url=...}` are
   everywhere in real scripts).
2. `_locs_lt`: total-order comparison for carried-locals tuples (int/None mixing
   crashed the backward-jump hub test).
3. `MAX_STACK_DEPTHS` limiter now keys on the stack-POINTER value, not the whole
   locs tuple — object-carrying states (decryptor Bufs, OpaqueFns) no longer
   exhaust the depth budget spuriously. Error markers 64 → 17 on RaceforEggs.
4. Walk `edges`/`pred` dicts are now walk-LOCAL (nothing ever read them) — holding
   them through `lower()` was the main OOM driver on deep proto chains.
5. `sys.intern` on `fmt_expr` output + `_carry_key` strings (state keys repeat
   these by the million) + periodic `gc.collect()` in `closure()`.

**OOM lesson (deep chains):** a single in-process lift of a ~119-deep nested proto
chain holds every ancestor's IR alive during `lower()` and OOMs a 4 GB container
(~85 % at depth ~65-81, two runs died). Fix = `DEVIRT_SHALLOW=1` (children become
`__DEVIRT_CHILD__(p<pid>|t<tid>)` markers) + `tools/lift_all.py` which lifts every
captured proto SEQUENTIALLY (walk state is walk-local now) and splices the markers
recursively. `tools/lift_child.py` lifts one tid standalone.

**Renderer guard:** `codegen.Renderer.lvalue` renders Const/raw-int assign targets
(a numeric-for recognition side effect) as `__SLOT_N__` so the output always parses
(luau-ast verified).

**Golden regression caveat (pre-existing, NOT from these changes):** at main-repo
HEAD e24ecb1 the two RUN_GOLDEN samples (5ae…, RideAPet) do not reproduce their
committed references IN THIS CONTAINER — the sandbox trace dies with
"table index is nil" (5ae = FlowAuth-protected loader; flowauth.net now 403s plain
GETs; RideAPet's loadstring'd chunk errors identically on the CLEAN tree). The goldens
were generated from the later lost luarmor commits (a5dcd4c/01ebbbd, wiped by a
container reset before push). With the session's changes the lifts COMPLETE where the
clean tree failed outright ("call of unknown VM function lf1"); npm test 36/36 green.

---

## 2026-09-29 (later) — ROUND-2: the grind is SOLVED, full capture obtained

**This is the big one.** All previous capture attempts (capture_v3/v4, /tmp/fresh_raw*.txt)
died with 0 bytes: the payload has an anti-analysis grind that OOMs the sandbox
(~80 MB/s, 3.6 GB in <60 s, SIGKILL, no output).

**Root cause chain (fully mapped, see FLOWAUTH_HANDOFF.md §6):**
1. `driver.patch_spin` regex matches **0 loop heads** in this build (`while true do
   if not(x<=15)then…` shape) → spin watchdog completely dead.
2. The one entry hook fires once (its `%128` gate skips the check; never re-runs).
3. The script swallows Lua-string errors via real pcall (envlog passes `E.pcall = R.pcall`
   on purpose — Luraph fingerprints the stack).
4. newP proxy abort never fires (grind allocates raw Lua objects, not proxies).
5. ulimit -v → GC-thrash forever at ~505 MB, still no clean exit.
6. ACTUAL mechanism: after the root enters the tamper-check fn (pid 3), a tamper-response
   handler loops INSIDE one VM instruction (dispatch head never re-executes).

**THE FIX** (`devirt_full.py`): inject `__SPIN` counting into EVERY `while true do` head
(65 sites): `re.subn(r"\bwhile true do ", ... + "if __SPIN then __SPIN.n=__SPIN.n+1;if
__SPIN.n>=__SPIN.step then __SPIN.f()end;end;", src)`. Clean abort at t≈30 s, rc=0,
full wrap-up: **164 MB dump = 423,934 protos / 428,962 tables / 20 entered pids / 695 lf
values** (vs 64 protos from the old capture). Trace proves real code ran: UI builders
(`Instance.new("UIScale")`, `TextButton2`, `UISizeConstraint`, `Vector2.new(25,1)`…).

**New artifacts:** `devirt_full.py` (full pipeline + grind kill + DEVIRT_TRACE_DEBUG mode),
`lift_new_capture.py` (staged lift), `flowauth_crack/work/payload_full.protos.json.gz`
(7.9 MB), `payload_full.trace.txt`, `FLOWAUTH_HANDOFF.md` (master handoff + continuous
paste-able prompt).

**Remaining lift blockers (precisely diagnosed, §8 of handoff):**
- env-slot helper binding: env table t10 (cap field A, 61 slots) holds runtime-helper
  closures, filled dynamically (no static `A[49]=function`), never bound by devirt.py's
  cap-field-only binding loop → "call of unknown VM function lf149" at stepper init.
- wrapper factory: symbolic factory returns a wrapper, not the VM closure (devirt.py:740).
- entered pids → caps at tid+1 (pid 1→t339806 root, 3→t8418, 4→t63, … — full list §8).
- Next: record the maker's symbolic-exec puts into A as (slot→node) bindings; follow the
  wrapper to the inner VM closure; lift the 20 entered protos.

**Env quirks that cost hours** (now in handoff §9): luau stdout block-buffered (killed
process = 0 B output); background processes reaped between tool calls (run foreground);
3.9 GB RAM box (grind OOMs the whole machine).

---

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
