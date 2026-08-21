# FROND — Project Tracker

Working document. Update `Status` as tasks move. Companion to `FROND_REDESIGN.md`
(the assessment and rationale) — this file is the executable breakdown.

Status legend: `TODO` · `WIP` · `DONE` · `BLOCKED` · `DROPPED`

---

## 0. Locked decisions

Recorded so they are not re-litigated. Change them here, deliberately, if they change.

| # | Decision | Consequence |
|---|---|---|
| **D1** | **Growth runs load → support (reversed).** | Every tip carries a known force vector. Thickness set at creation via `A = |F|/σ`; Murray derived from vector equilibrium, not assumed; load paths closed by construction. No bidirectional variant for now. |
| **D2** | **All three cycle mechanisms are implemented, and must be independently switchable *and* combinable.** | Multi-support flow splitting, multi-load-case union, and buckling-driven bracing are three orthogonal flags on the generator — not alternatives. Phase 4 must produce an ablation across the 2³ combinations. |
| **D3** | **Merging is the Maxwell–Michell cost test, never a distance test.** | `anastomosis_radius` does not exist in the new code. Any reintroduction of a proximity-based fusion parameter is a regression. |
| **D4** | **No skeletonized-SIMP comparison.** Benchmarks must be direct. | Comparison strategy is deferred (see Open Decisions O1), but the evaluator in Phase 2 must be built **pluggable** so a continuum evaluation path stays available. Do not hard-wire the frame FE as the only evaluator. |
| **D5** | Framing stays open: FROND may compete on stiffness *and* mass simultaneously. | Do not write the "reparameterization, not competitor" framing into the code or the benchmark design yet. Decide from results. |

### Open decisions

| # | Question | Needed by |
|---|---|---|
| **O1** | How to compare FROND against SIMP *directly*, given one is a frame model and the other a continuum. Leading candidate: evaluate **both** designs in the same continuum FE (render the FROND frame to a body-fitted or high-resolution density mesh) — i.e. lift FROND into SIMP's evaluation space rather than reducing SIMP into FROND's. | Phase 2 (affects evaluator architecture) — discuss before P2-5 |
| **O2** | Allowable stress model: single σ_allow, or separate σ_tension / σ_compression? The latter is more realistic and interacts with buckling. | Phase 3 |
| **O3** | Are load quanta fixed in magnitude and position, or may the generator redistribute them along Γ_l? | Phase 3 |

---

## Phase 0 — Hygiene

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P0-1 | `git init` | Repo initialized | **DONE** |
| P0-2 | `.gitignore`; untrack `__pycache__`; move legacy figures to `docs/legacy/`; delete `scratch/` and `implementation_plan.md` | `git ls-files` contains no `.pyc`, no generated output | **DONE** |
| P0-3 | Seed every RNG; thread a `seed` argument through the whole pipeline | Two runs with the same seed produce byte-identical graphs | TODO |
| P0-4 | Pin dependency versions in `pyproject.toml`; add `pytest` config | `pip install -e ".[dev]"` reproducible from clean env | TODO |
| P0-5 | Decide package layout: rewrite in-place vs `frond/` (new) + `legacy/` (old, read-only reference) | Layout committed; old code still runnable for "before" figures | TODO |

---

## Phase 1 — Domain, benchmarks, baseline

Goal: be able to *measure* before being able to *generate*.

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P1-1 | `Domain`: Γ_s / Γ_l / Γ_d with conductance flag, arc-length parameterization, point-in-domain and clip-to-domain queries | Unit tests on rectangle and L-shape, incl. reentrant corner | TODO |
| P1-2 | Load-quanta discretization of Γ_l: N points, each with force vector **f**ᵢ, Σ**f**ᵢ = applied load | `assert np.allclose(sum(f_i), F_total)`; convergence check as N increases | TODO |
| P1-3 | Benchmark: MBB beam (half-symmetry) | BCs verified against the reference definition, not invented | TODO |
| P1-4 | Benchmark: cantilever | as above | TODO |
| P1-5 | Benchmark: L-bracket | as above; fix the current corner-seeding and span errors | TODO |
| P1-6 | Benchmark: Michell point-loaded cantilever (has a closed-form optimum) | Analytic Michell volume recorded as an absolute reference | TODO |
| P1-7 | **SIMP baseline** (top88-style, ~100 lines), validated | Reproduces published compliance for MBB at standard vol. fraction | TODO |

---

## Phase 2 — FE and validation ⛔ **GATE**

**Nothing in Phase 3+ may start until every task here passes.** The current project's
core failure is a generator paired with an evaluator that returns 0.0 for a structure
that never reaches the load.

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P2-1 | Planar intersection resolution: `STRtree` query, split members at crossings, merge coincident nodes within tol | `assert crossing_pairs_without_shared_node == 0` on all benchmarks (currently **221** on the L-bracket) | TODO |
| P2-2 | Frame FE: assemble, fix Γ_s DOFs, distribute Γ_l loads | — | TODO |
| P2-3 | **Hard error when no node reaches the load boundary** | Raises, never returns 0.0 | TODO |
| P2-4 | Singularity / rigid-body-mode detection — inspect the factorization, do not rely on `spsolve` raising | Mechanism returns `inf`, and a test constructs a known mechanism to prove it | TODO |
| P2-5 | Pluggable evaluator interface (see D4/O1) | Frame evaluator and a stub continuum evaluator share one interface | TODO |
| P2-6 | Validate against a 2-bar truss with hand-computed compliance | Matches analytic to ~1e-10 | TODO |
| P2-7 | Validate against SIMP baseline on a uniform grid frame | Agreement within a documented tolerance | TODO |
| P2-8 | Fully-stressed sizing `A = |F|/σ` as a standalone, tested routine | Recovers the analytic 2-bar optimum | TODO |

---

## Phase 3 — Flow-growth engine

Implements `FROND_REDESIGN.md` §2.1–2.4.

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P3-1 | Tip state: position, force vector **F**, `tree_id`; array-backed, not dict-of-objects | — | TODO |
| P3-2 | Seeding on Γ_l from load quanta; non-degenerate seeding on Γ_s (no corner seeds) | Regression test: no seed coincides with a domain corner | TODO |
| P3-3 | Advance step toward nearest sink, with domain clipping | Tips never exit the domain | TODO |
| P3-4 | **Maxwell–Michell merge test** with Steiner-point placement (§2.3) | Unit test: near-collinear flows merge; near-perpendicular flows do not; **no length-scale parameter appears anywhere in the test** | TODO |
| P3-5 | Boundary flow semantics: Γ_d conductance 0 (Mode B) vs conducting spine (Mode A) | Mode B: no tip terminates on Γ_d. Mode A: spine area profile `A(s) = |F(s)|/σ`, zero where no flow | TODO |
| P3-6 | Termination on Γ_s; record reactions | Σ reactions balances Σ applied load | TODO |
| P3-7 | **Dead-weight validator**: `assert f_e != 0 for every e` | Passes on all four benchmarks in both modes; replaces `cleaning.py` entirely | TODO |
| P3-8 | Delete `cleaning.py`, `interactions.py` (old), `spines.py` (old), `growth.py` (old) | Old modules gone or moved to `legacy/` | TODO |

**Phase 3 deliverable:** Modes A and B on all four benchmarks, `f_e ≠ 0` holding for every
member, zero unresolved crossings, and figures showing the venation artefact is gone.

---

## Phase 4 — Cycles and triangulation

Per **D2**: three independent, combinable mechanisms.

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P4-1 | Mechanism A — multi-support flow splitting | Cycles appear when a load's flow reaches two supports; split fraction is a recorded variable | TODO |
| P4-2 | Mechanism B — multi-load-case union | Per-case networks generated and unioned; cycle count > 0 | TODO |
| P4-3 | Mechanism C — buckling-driven bracing (`σ_cr ∝ A/L²`) | Long slender compression members trigger intermediate bracing | TODO |
| P4-4 | Composability: A/B/C as orthogonal flags | All 2³ combinations run without error | TODO |
| P4-5 | **Ablation study** across the 8 combinations on all benchmarks | Table: cycle count, compliance, volume, member count per combination | TODO |
| P4-6 | Populate the 2×2 typology (1 vs k seeds × Mode A vs B) with real figures | `FROND_REDESIGN.md` §2.6 table filled in | TODO |

> **Note on D5 / your thin-web intuition.** Thin webs give low mass for a given axial
> stiffness, which is why the mass claim is plausible — but thin webs are exactly what
> buckles. Mechanism C (P4-3) is therefore not optional decoration; it is what determines
> whether the mass advantage survives contact with stability. Run the ablation with and
> without it before making any mass claim.

---

## Phase 5 — Sizing and shape refinement

The largest single source of improvement. Topology fixed; two cheap gradient stages.

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P5-1 | Sizing: optimality-criteria / fully-stressed iteration on member areas | Monotone compliance decrease at fixed volume | TODO |
| P5-2 | Analytic sensitivities w.r.t. node positions | Verified against finite differences to ~1e-6 | TODO |
| P5-3 | Shape refinement: gradient-based node-position optimization | Nodes stay in domain; no member inversion; improvement quantified vs raw layout | TODO |
| P5-4 | Re-run the dead-weight and crossing validators after refinement | Both still pass | TODO |

---

## Phase 6 — Outer loop over growth parameters

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P6-1 | Consolidate generative parameters into one typed, documented struct (~10 params) | No magic numbers left in the engine | TODO |
| P6-2 | CMA-ES or Bayesian optimization over the parameter set | Converges on the cantilever benchmark | TODO |
| P6-3 | **Replicate handling**: each candidate evaluated as the mean over R seeded replicates | R chosen from a documented variance study | TODO |
| P6-4 | Report variance, not just means, in every result | Every reported figure carries a spread | TODO |

---

## Phase 7 — Benchmarking and paper

| ID | Task | Acceptance criterion | Status |
|---|---|---|---|
| P7-1 | Resolve **O1** and implement the direct comparison protocol | Protocol written down and agreed before any numbers are generated | BLOCKED on O1 |
| P7-2 | Compliance–volume **Pareto fronts**, FROND vs SIMP, all benchmarks | Fronts, not single points | TODO |
| P7-3 | Michell analytic bound overlaid where it exists | — | TODO |
| P7-4 | Design-variable count comparison | — | TODO |
| P7-5 | Mesh-independence study | FROND result invariant to evaluator mesh refinement | TODO |
| P7-6 | Solution-diversity figure (family of near-optimal designs from stochastic seeding) | — | TODO |
| P7-7 | Literature positioning: Michell, Maxwell, ground-structure TO, Runions, Bejan/constructal, Kelly & Elsley, adaptive-growth methods | Related-work section drafted | TODO |
| P7-8 | **Rewrite `FROND_CONCEPTS.md`** — it currently documents the CANOPY L-system engine, which does not exist in the code | Concepts doc matches the implemented method | TODO |

---

## Immediate next actions

1. **P0-5** — decide the package layout (rewrite in place vs `frond/` + `legacy/`). Blocks everything else.
2. **P0-3, P0-4** — determinism and pinned deps. Cheap, and P6-3 depends on determinism.
3. **P1-7** — the SIMP baseline. Start it early; it is on the critical path for Phase 2 validation *and* Phase 7, and it is independent of every FROND design decision.
4. **O1** — schedule the benchmark-comparison discussion before P2-5.
