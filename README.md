# FlowAuth-Deobfuscator

Standalone crack + devirtualization pipeline for **flowauth.net** protected Roblox
scripts (FlowAuth v3 protocol / Luraph v15 payload). Split out of
[Deobfuscator-Luraph-V15](https://github.com/Aditya-lua/Deobfuscator-Luraph-V15) —
that repo keeps the sandbox harness (`runtime/envlog.luau`), the Luau binary and the
generic devirt core (`src/vmmap`, `core/devirt.py`); this repo holds everything
FlowAuth-specific.

## Layout

| Path | What it is |
|------|-----------|
| `flowauth_crack/` | The chain tooling: fresh-loader fetch, envlog patcher, one-process live chain, payload reassembler |
| `flowauth_crack/work/` | Run products (gitignored): fresh `loader.lua`, `bootstrapper.lua`, `canned.json`, hop responses, `chunks/`, `payload_source.lua` |
| `flowauth_capture/` | Tracked artifacts of the successful capture: `payload_source.lua` (713,630 B — LRM prelude + Luraph v15 VM), VM state dump (`capture_protos.json.gz`, 64 protos / 4,986 tables), behaviour trace, hop responses, round-1 lift |
| `*.py`, `*.js`, `shadow_libs.luau` (root) | Devirt probes: detection → VM match → proto walk → lift |

## The chain (all automated in ONE luau process)

```
flowauth.net /v1/loaders/<md5>.lua          fresh loader (launch_ticket inside, SINGLE-USE)
  └─► downloads FlowAuthRuntime (586,282 B, Luraph v15 bootstrapper, Adler-32 verified)
        └─► /v1/auth/challenge ─► /v1/auth/script (runtime_keys.onyx-v1, 2 chunk tokens)
              └─► /v1/auth/payload x2 (one URL, token in body, reqbody-pinned plant)
                    └─► two 384 KB-split raw-lz4 blocks ─► 713,630 B PAYLOAD
```

`launch_ticket` is single-use (401 `launch_ticket_rejected` on replay) → every run
fetches a fresh loader.

## Usage

```bash
# hop-by-hop chain (fresh loader → auth → payload chunks)
python3 flowauth_crack/flowauth_chain.py

# one-process end-to-end (live fetch loop + NEEDFETCH/__LRMRES serve contract)
python3 flowauth_crack/flowauth_two_phase.py

# reassemble the payload python-side (bypasses the runtime's own lz4 step)
python3 flowauth_crack/reassemble_payload.py
```

The devirt core (`src/vmmap`, `core/devirt.py`, `bin/luau`) still lives in the
main repo; scripts here reference it via absolute path.

## Status

- Full FlowAuth v3 protocol reversed + automated; payload captured & tracked.
- Payload's own VM build detected: **while-form dispatch, group-wrapped fetch head
  (`local w=(V[f])`), proto decoded inside the interpreter closure
  (`C=function(...) ... A[113](x) ...`), factory `(A)[0x3c]=function(W,m)`** —
  a second Luraph v15 build family (dispatch_local).
- Round-1 lift: `flowauth_capture/payload_lift.lua` — 53 functions / 8.7 KB,
  anti-tamper checklist visible (`islclosure`, `"IsClient"`, `Random NextInteger`,
  `buffer readu32`, `"AnchorPoint"`, ...).
- Remaining gaps: junk-guard walk errors, unbound helper calls (`lf141`/`lf155`),
  vararg rendering, lazy constants still need the live-fetch loop.
