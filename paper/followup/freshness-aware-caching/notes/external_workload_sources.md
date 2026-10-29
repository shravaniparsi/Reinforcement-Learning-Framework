# External workload source registry

Date checked: 29 October 2026

These records identify candidate source code only. No upstream performance observations enter the study.

## SvelteKit RealWorld feed

- Repository: `https://github.com/sveltejs/realworld`
- Pinned commit: `df796708040f5200ec572b28ab7f88ecee5794dd`
- License: MIT, retained locally at `experiments/external/svelte-realworld/LICENSE.upstream`
- Existing local status: the prior adaptation is read-only and uses a synthetic local article API. A new patch and mutable backend are required for this study.
- Inclusion gate: controlled mutations, snapshot-consistent feed oracle, frozen production build and unchanged displayed semantics across policies.

## React-admin e-commerce dashboard

- Repository: `https://github.com/marmelab/react-admin`
- Pinned commit: `0c33d9c3c27cc4bf97e11f56080c5bfe182f2f2a`
- Upstream commit date: 28 October 2026
- Selected path: `examples/demo`
- License: MIT; `LICENSE.md` blob at the pinned commit is `5ccf945870004aa6bab026158794b8d582bfcfbd`
- Upstream behavior: the demo describes its API as browser-simulated FakeRest data. The dashboard reads orders and derives revenue, new-order counts and pending orders; it also renders pending-review and new-customer panels.
- Adaptation status: `controlled-backend.patch` replaces FakeRest with the controlled mutable origin, fixes the study clock, removes remote font requests and adds nonvisual oracle identifiers. The locked standalone production build passed.
- Inclusion-gate status: the deterministic multi-entity reset, historical snapshot oracle and browser-visible dashboard checks passed on 29 October 2026. Cache-policy equivalence remains part of the common gateway gate.

## Source-use rule

Each source must be fetched from its pinned commit, built with locked dependencies and accompanied by the upstream license and adaptation patch. If a pinned source cannot meet its inclusion gate, it is excluded before confirmatory collection and the protocol is amended before replacement.
