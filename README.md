# FlowAuth-Deobfuscator

> Tool by **@adi.codz** (Discord) — see [AUTHORS.md](AUTHORS.md).

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

The fetcher works on **any** `flowauth.net/v1/loaders/<md5>.lua` URL — it fetches
a fresh loader, downloads + verifies the current stage-2 runtime, runs the auth
handshake in the Luau sandbox, and reassembles the raw obfuscated payload.

```bash
# the Luau sandbox (bin/luau + runtime/envlog.luau + core/harness.py) lives in the
# Deobfuscator-Luraph-V15 repo; point at it once (or let it auto-discover a sibling):
export FLOWAUTH_REPO=/path/to/Deobfuscator-Luraph-V15

# one-process end-to-end fetch for ANY loader URL -> work/<md5>.payload.lua
python3 flowauth_crack/flowauth_two_phase.py \
  --loader-url https://flowauth.net/v1/loaders/<md5>.lua

# inspect / fetch just the stage-2 runtime for a URL (pure Python, no sandbox)
python3 flowauth_crack/flowauth_loader.py https://flowauth.net/v1/loaders/<md5>.lua -o runtime.lua

# hop-by-hop chain (older driver; fresh loader → auth → payload chunks)
python3 flowauth_crack/flowauth_chain.py --loader-url https://flowauth.net/v1/loaders/<md5>.lua

# reassemble the payload python-side (bypasses the runtime's own lz4 step)
python3 flowauth_crack/reassemble_payload.py
```

`--repo PATH` overrides the sandbox location; otherwise `FLOWAUTH_REPO` or a sibling
`Deobfuscator-Luraph-V15` / `deobfuscator-luraph-v15` directory is auto-discovered.
The devirt core (`src/vmmap`, `core/devirt.py`, `bin/luau`) still lives in the main repo.

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

## Support / Donate

<div align="center">
  <img src="assets/donate/donate_header.png" width="520" alt="Buy me a coffee — fund future projects">
</div>

If these tools are useful to you, you can help fund future projects by sending
crypto to the addresses below. Thank you for the support. — **@adi.codz** (Discord)

| Network | Address | Scan |
|---|---|---|
| **Bitcoin** (BTC) | `bc1q3nprh6e0y4fz88ft4uu5dad7xsx629z498dkay` | <img src="assets/donate/btc.png" width="120" alt="Bitcoin QR"> |
| **Ethereum** (ERC-20) | `0x11369a1d18eb442581D1e675dAdD94eBA1c4bE52` | <img src="assets/donate/eth.png" width="120" alt="Ethereum QR"> |
| **BNB Smart Chain** (BEP-20) | `0x11369a1d18eb442581D1e675dAdD94eBA1c4bE52` | <img src="assets/donate/bnb.png" width="120" alt="BNB Smart Chain QR"> |
| **Solana** (SOL) | `AVKBDNT2PzYDJ7njVrjt7MoVZ1tY4DvNSsADdujiGKTC` | <img src="assets/donate/sol.png" width="120" alt="Solana QR"> |
| **Litecoin** (LTC) | `ltc1qu4ahsjff622xqjlqwafhlgmacd5ea477sqpx9z` | <img src="assets/donate/ltc.png" width="120" alt="Litecoin QR"> |

> Send each asset only on its own network. ETH and BNB share one EVM address —
> use it for ERC-20 on Ethereum and BEP-20 on BNB Smart Chain. Assets sent on the
> wrong network may be lost.
