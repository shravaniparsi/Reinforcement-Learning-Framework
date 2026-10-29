# W2 mutable SvelteKit RealWorld adapter

Status: clean build and semantic browser gate passed on 2026-10-29. No performance collection is authorized.

## Source boundary

- Upstream application: `https://github.com/sveltejs/realworld`
- Pinned commit: `df796708040f5200ec572b28ab7f88ecee5794dd`
- Upstream license: MIT, retained at `experiments/external/svelte-realworld/LICENSE.upstream`
- Prior study adaptation: `production-variants.patch`, which remains unchanged
- New incremental study adaptation: `freshness-api.patch`

The incremental patch changes only the loopback API port from the prior read-only fixture on 3205 to the new mutable origin on 3206. Apply it after `production-variants.patch` to a clean checkout at the pinned commit. It does not contain cache-policy logic.

## Origin behavior

`realworld_workload.py` stores versioned article snapshots in SQLite. It supports controlled create, update and delete commits. Historical query reconstruction covers:

- article membership under declared tags;
- feed ordering;
- pagination;
- title, description, body and tags; and
- the complete RealWorld article representation returned to the UI.

The ETag derives from the complete query response. An update that does not change a query result therefore permits a 304 response even though the origin's global commit revision advanced.

`realworld_service.py` exposes `/api/articles` and `/api/tags` on loopback. Mutation and reset endpoints require a controller header and reject browser-originated requests.

## Semantic checks

Run the pure workload tests:

```sh
python3 -m unittest tests.test_freshness_realworld_workload
```

Run the loopback HTTP checks:

```sh
python3 -m unittest tests.test_freshness_realworld_service
```

These checks do not record latency or produce study observations.

The clean application gate uses a checkout reconstructed from the pinned commit. Apply
`production-variants.patch`, then `freshness-api.patch`, install with pnpm 10.20.0 and
the frozen lockfile, and build with Node 20.19.6:

```sh
PUBLIC_PILOT_SSR=true PILOT_BUILD_OUT=build-freshness pnpm run build
```

Run the end-to-end semantic gate from the repository root:

```sh
.venv/bin/python experiments/freshness/realworld_browser_smoke.py
```

The gate starts the mutable origin and the production Node adapter on loopback. It
checks SSR HTML and hydrated browser content against the current origin response after
title update, tag membership change, create and delete operations. It blocks external
requests and records no latency. The 2026-10-29 engineering result is stored at
`data/engineering/freshness-w2-browser-smoke-v1/results.json`.

## Remaining W2 gates

1. Add the common cache-policy gateway without changing the Svelte UI or origin semantics.
2. Verify reset, trace identity and fault-schedule identity across every policy.
3. Freeze a source and build manifest before any timing engineering begins.
