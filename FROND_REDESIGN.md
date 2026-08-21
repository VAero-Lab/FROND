# FROND — Assessment and Redesign Plan

Status: written after auditing `frond/` (1426 LOC), `FROND_CONCEPTS.md`, `frond.png`,
and running the pipeline on the L-bracket benchmark.

---

## Part 1 — Assessment of the idea

### 1.1 What is genuinely good

Three things in your proposal are real contributions and should survive any rewrite.

**(a) The three-tier boundary semantics (Γ_s / Γ_l / Γ_d).** In density-based TO, boundary
conditions are inert nodal constraints. Giving them *generative* meaning — supports emit,
loads attract, design boundaries constrain and optionally conduct — is a genuine
reframing, and it is the part of FROND that is hardest to get from SIMP. Keep it and
make it precise (see §2.4).

**(b) The insistence that every member lie on a closed load path.** You identified the
correct failure mode (dangling dead weight) and the correct requirement. What you have not
yet found is the right *formal* statement of it, which is what makes the current fusion
heuristic misbehave. §2.3 gives it.

**(c) The forest / multi-trunk concept, and your observation that interaction forces
truss-like rather than tree-like results.** This is correct and it is the most interesting
structural claim in the project. It deserves to be the paper's organising typology
rather than an implementation detail — see §2.5.

### 1.2 The central problem with the idea as currently framed

> **The space colonization algorithm is a space-*filling* algorithm. A structure is a
> force-*routing* object. Applying SCA unmodified produces leaf venation, not a load path.**

This is not a tuning problem, and it is exactly what the current output shows: the
generated L-bracket is a dense reticulate venation network that uniformly fills the
domain. SCA's competence — reach a cloud of attractors with low total length — is a
*Steiner-like* objective over a prescribed point set. Nothing in it knows about statics.
So the quality of the result is entirely determined by *what the attractors mean*, and
right now they mean "empty space", which is why you get a leaf.

There is a second, deeper issue that follows from it:

> **Growth from support → load runs *against* the direction of force flow.**

Force flows load → support. If you grow from the support, a growing tip does not know how
much force it will eventually carry, because that depends on what happens downstream —
which is why the current code has to apply Murray's law retroactively, as a post-hoc
recursion over a graph that by then contains loops (and consequently produces the thickness
blow-ups documented in §1.3). Every quantity that matters — thickness, merge decisions,
whether a branch is dead weight — is unavailable at the moment the algorithm has to decide.

The reconceptualization in Part 2 fixes both by changing what an attractor is and which
way growth runs. Your biological framing survives intact: growth from load to support is a
**root system** (or a river network draining to an outlet), which is arguably a *better*
analogy for a structure whose job is channelling force to ground than a canopy is.

### 1.3 Audit of the current implementation

Run on `Benchmarks.l_bracket()` with the `test_cleaning.py` parameters, seeded:

```
growth steps = 499 (hit the iteration cap; attractors never consumed)
after growth  : 637 nodes, 816 branches
after prune   : 151 nodes, 333 branches
thickness     : min 1.000, max 21.708  (base_thickness = 1.0)
CROSSING member pairs with NO shared node: 221
nodes exactly on the LOAD boundary       : 4
compliance = 0.0138, volume = 6895
```

**Physics-invalidating defects** (results from this pipeline are not meaningful):

1. **221 pairs of members cross in the plane without sharing a node.**
   `InteractionEngine.resolve_intersections` is a `pass` with a comment claiming SCA makes
   it unnecessary. It does not. In 2D, two members that cross *must* share material. The FE
   model therefore lets members pass through each other, which makes the structure far more
   compliant than it looks and makes the compliance number meaningless.

2. **Spines are structurally disconnected from the branches touching them.**
   `SpineManager.materialize_spines` creates one edge per *boundary vertex pair* — the
   diagnostic shows spine edges of length 40, 60, 60, 100 with degree 2 at both ends. A
   100-unit spine is a single frame element with nothing attached along it. Branch tips that
   snapped onto the spine line are separate nodes that never connect. The claimed
   "1.6×–6.7× improvement from material spines" in `FROND_CONCEPTS.md` cannot have come
   from this code.

3. **Zero load ⇒ zero compliance ⇒ global optimum.** In `FEASolver.compute_compliance_and_mass`,
   if no node lands within `1e-6` of the load boundary, `load_nodes` is empty, `F` stays
   zero, and the function returns compliance `0.0`. `FrondOptimizer.evaluate` would rank a
   structure that never reaches the load as the best possible design. Only 4 nodes out of
   151 touch the load boundary here, so this is a live hazard, not a theoretical one.

4. **Singular systems are not detected.** `spsolve` on a disconnected or mechanism-like
   structure returns garbage with a warning rather than raising, so the `except Exception`
   guard never fires and `inf` is never returned.

**Defects that directly cause the artefacts you dislike:**

5. **Attractors are seeded 70% uniformly in the domain, 30% on *all* boundaries** — and
   `attractor_is_load` is set `True` for every boundary attractor, including purely
   geometric ones. So the entire perimeter attracts growth and acts as a snap target. This
   is the single line most responsible for the venation appearance.

6. **`radius_of_influence` = 60–80 on a 100-unit domain is effectively global.** The growth
   direction is the average unit vector to every attractor in range, so it points roughly at
   the domain centroid. Hence the meandering central trunk.

7. **No real bifurcation rule.** A tip advances one step in a single averaged direction and
   *stays* a tip, so it may sprout again next step from the same node. Genuine branching
   only happens by accident, which is why you get long wandering paths with small spurs
   instead of a branching hierarchy. Classical SCA splits by *clustering* the attractors in
   range into direction groups; that is missing.

8. **Anastomosis is a pure proximity test.** A new candidate point fuses to any node within
   `anastomosis_radius`, regardless of angle, of which tree the target belongs to, or of
   whether the fusion is useful. This is precisely the pathology you named: it manufactures
   very short, near-parallel connections and sliver triangles. §2.3 replaces it.

9. **Retroactive Murray on a graph with cycles is ill-posed.** `apply_murrays_law` recurses
   with a `visited` set that returns `base_flow` on cycle detection — an arbitrary
   tie-break, not a conservation law. Result: 21.7× thickness range and the black blobs in
   `test_pruned.png`.

10. **Pruning uses the wrong anchoring test.** `prune_dangling` keeps any leaf within 2.0 of
    *any* boundary — including non-material geometric boundaries, which react against
    nothing. Dead weight is retained by design. It is also O(N²) (rebuilds adjacency and
    restarts after each single removal).

11. **Seeds land on boundary corners.** `ForestGenerator.generate_seeds` uses
    `np.linspace(0, length, n)`, so for n=3 on the L-bracket support edge the seeds are
    (0,100), (20,100), (40,100) — two of the three are corners of the domain.

**Methodological defects:**

12. **`FrondOptimizer` contains no optimizer** — only `evaluate`, which nothing calls. Its
    design vector is 6 *global growth hyperparameters*, and the generator calls
    `np.random.uniform` with no seed, so the objective is stochastic and non-reproducible.
    Optimising a noisy 6-parameter black box is not a credible answer to SIMP's
    gradient-based optimisation over 10⁴–10⁶ variables.

13. **There is no baseline.** No SIMP implementation, no ground-structure comparison, no
    Michell reference. There is currently no way to tell a good FROND result from a bad one.

14. **`FROND_CONCEPTS.md` describes a different program than the one in `frond/`.**
    The document details branching modes, apical dominance, `dominance_factor`,
    reference frames, `SubParams`, `crossing_mode` — an L-system engine inherited from
    CANOPY. `growth.py` is pure SCA and contains none of it. The conceptual spine of your
    paper currently documents code that does not exist.

15. Not a git repository. Before a rewrite of this scale, `git init`.

---

## Part 2 — The reconceptualization

Six changes. Together they turn FROND from "SCA applied to a bracket" into a method with
its own mathematical identity.

### 2.1 Attractors carry force, not resource

Discretize Γ_l into N quanta, each a point **p**ᵢ with a force vector **f**ᵢ, with
Σ**f**ᵢ equal to the applied load. **These are the only attractors.** No interior
attractors, none on geometric boundaries. This one change removes the venation.

An attractor is no longer "consumed" — it is *discharged*: a branch that reaches it takes
on its force.

### 2.2 Grow along the flow: load → support

Reverse the growth direction. Every growing tip then carries a **known accumulated force
vector F**, and three things that are currently hacks become free:

- **Thickness is set at creation.** Fully-stressed design: A = |**F**| / σ_allow. No
  retroactive pass, no cycle ambiguity, no blobs.
- **Murray's law is derived, not assumed.** At a merge, A_parent = |Σ**F**_child| ≤
  Σ|**F**_child|, with equality only for collinear children. The exponent stops being a
  free parameter — it is a consequence of vector equilibrium. (Document this as a
  *departure* from the biological n=2/n=3 form, and as a strength.)
- **Reaching Γ_s closes the load path by construction.**

You lose the root-collar-to-canopy narrative and gain a root-system / river-network one.
For a structure that must channel force to ground, the second analogy is stronger, and it
connects you directly to **Bejan's constructal theory** (flow architectures generated by
tree-like growth), which gives the whole approach an established theoretical footing that
"we used the CGI tree algorithm" does not.

### 2.3 Merging is a cost comparison, not a distance test

This is the direct answer to your sticking point. Two tips at **x**₁, **x**₂ carrying
**F**₁, **F**₂. Use the Maxwell–Michell transport cost, which for a fully-stressed
structure *is* its volume:

> W = Σ_e |**F**_e| · L_e   (since V = Σ A_e L_e = Σ |**F**_e| L_e / σ)

Merge at a Steiner point **x*** iff

> |**F**₁+**F**₂|·L(**x***→support) + |**F**₁|·‖**x**₁−**x***‖ + |**F**₂|·‖**x**₂−**x***‖
> &nbsp;&nbsp;<&nbsp;&nbsp; |**F**₁|·L₁ᵃˡᵒⁿᵉ + |**F**₂|·L₂ᵃˡᵒⁿᵉ

**Why this fixes the pathology.** The inequality is satisfied when the two flows are
near-collinear (merging saves length at little vector-cancellation cost) and violated when
they are near-perpendicular (|**F**₁+**F**₂| approaches Σ|**F**ᵢ| and you have added length
for nothing). Short, near-parallel sliver connections — the artefact you are seeing — are
exactly the case the criterion *rejects*, because they cost length while saving none. The
optimal junction satisfies the Steiner/Michell equilibrium condition on the three force
vectors, which sets the branch angles automatically. **No `anastomosis_radius` parameter
exists anymore.** That is the point: the arbitrary length scale is gone.

This also states what FROND *is*, mathematically: a growth heuristic for the
**weighted Steiner / Michell layout problem under domain constraints with typed
boundaries**. That is a far more defensible framing than "bio-inspired alternative to SIMP".

### 2.4 Boundaries become flow objects

| Boundary | Flow role | Mode |
|---|---|---|
| Γ_l (load) | **Source.** Carries the force quanta. | always |
| Γ_s (support) | **Sink.** Flow terminates; reactions. | always |
| Γ_d (geometric) | **Obstacle**, conductance 0. Tips may not terminate on it. | Mode B |
| Γ_d (geometric) | **1-D conductor** ("spine"). Absorbs flow anywhere along its length and transports it to a support. | Mode A |

Your two modes are now just the conductance of Γ_d. And there is a bonus:

> You asked how much of a geometric boundary should be solid, and wanted it determined
> during optimisation. Under the flow formulation it is **computed, not searched**: the
> spine's cross-section at every point is A(s) = |F(s)|/σ, and where no flow passes, the
> area is zero. Partial spine extent falls out of the algorithm instead of being a design
> variable.

Note also that CANOPY's *clipping* and *extension* repairs disappear: a tip either
terminates on a conducting boundary or is disallowed from leaving the domain. No
post-hoc repair.

### 2.5 The forest, formalized — and why dead weight becomes impossible

Represent the structure as a **flow network** (V, E, **f**) with **f**: E → ℝ², subject to
equilibrium at every node:

- div **f** = **f**ᵢ at load nodes (source)
- div **f** = reaction at support nodes (sink)
- div **f** = **0** everywhere else

Then:

- a **tree** = a connected component of the flow support rooted at one seed;
- a **forest** = the collection of them;
- **tree interaction = confluence of flow** — automatic in a flow network, not an added rule;
- and, one line, rigorous, checkable:

> **No dead weight ⟺ f_e ≠ 0 for every e ∈ E.**

If the generator only ever creates a member in order to carry nonzero flow, and equilibrium
holds at every node, then no member is dead weight *by construction*. `cleaning.py` stops
being a repair stage and becomes a one-line assertion. This is the formal statement you
were reaching for, and it is the strongest single result in the redesign.

### 2.6 Where the cycles come from

A pure Michell/Steiner flow network is a **tree** — it has no cycles, and a tree is a
mechanism under any load other than the one it was designed for. Your instinct that trunks
"must interact" is right; the honest question is what *forces* triangulation. Three
mechanisms, none of which is a proximity hack:

1. **Multiple supports.** With k support seeds, flow from one load may split toward
   different supports. Cycles appear exactly where a load's flow reaches two supports. The
   split fraction is a mechanically meaningful decision variable.
2. **Multiple load cases.** Grow the network for each load case and take the union. Cycles
   between the per-case networks are precisely the members that make the structure stiff
   for *both* cases. This is the cleanest way to force truss-like output, and it is
   defensible: real structures are multi-load-case objects.
3. **Buckling.** A Michell network ignores stability. Adding σ_cr ∝ A/L² penalizes long
   slender compression members and forces intermediate bracing — which *is* triangulation,
   and it is the actual physical reason trusses are triangulated.

This turns your observation into a typology that can organise the paper:

| | Γ_d transparent (Mode B) | Γ_d conducting (Mode A) |
|---|---|---|
| **1 seed** | cantilever tree; bending-dominated; expect it to lose to SIMP — report it honestly as the boundary of the method | spoke-and-rim; the rim reacts the tips |
| **k seeds** | **truss / Michell-like — the competitive mode** | truss + perimeter frame |

---

## Part 3 — Positioning against density-based TO

Be blunt with yourself about this, because a reviewer will be.

**You will not beat SIMP on compliance at equal volume, and you should not claim to.**
SIMP is a gradient method that is locally optimal for exactly that objective over a far
richer design space. FROND searches a restricted, generatively-parameterized subspace.

The defensible claims, in order of strength:

1. **Generative parameterization as dimensionality reduction for TO.** ~10 growth
   parameters + per-member areas, versus 10⁴–10⁶ densities. This is the real story.
2. **Discrete and manufacturable by construction.** No grey, no checkerboard, no
   thresholding, no skeletonization. Explicit members with explicit cross-sections.
3. **Mesh independence.** Length scale is set by the growth process, not by a filter radius
   on a background grid.
4. **Guaranteed topological properties.** Connectivity, no floating material, bounded member
   count, minimum member length — all enforceable at generation time, not checked after.
5. **Solution diversity.** Stochastic seeding yields a *family* of near-optimal designs.
   SIMP gives one.

**The fair benchmark**, and the one you can actually win or tie:

> FROND vs (i) SIMP thresholded and skeletonized into a frame, and (ii) classical
> ground-structure truss TO — all three evaluated with the **same frame FE** at the
> **same volume**, reported as a compliance–volume **Pareto front**, not single points.

Add Michell's analytical bound wherever it exists (the point-loaded cantilever has known
closed-form optima) as an absolute reference.

**Literature you must engage with**, because reviewers will ask:

- Michell (1904); Maxwell's load-path lemma.
- Ground-structure truss topology optimization (Dorn–Gomory–Greenberg; Bendsøe & Sigmund).
  **FROND is best described as a growth-generated *adaptive* ground structure** — this is
  the single most useful reframing for positioning the paper, and much stronger than "vs SIMP".
- Runions et al. (2005), space colonization for trees and for leaf venation — the SCA origin,
  and the reason unmodified SCA gives you venation.
- Bejan, constructal theory — flow architectures from tree-like growth.
- Kelly & Elsley, load-path theory — directly relevant to "valid load path".
- Adaptive-growth structural methods (Ding & Yamazaki and successors); ETH/Block group work
  on branching structures.

---

## Part 4 — Reuse or rewrite

**Verdict: rewrite the engine, port the chassis.** Roughly 350 of 1426 lines survive.

| File | Verdict | Notes |
|---|---|---|
| `domain.py` | **keep, extend** | Boundary typing is sound. Add conductance, load quanta discretization, arc-length parameterization. |
| `plot.py` | **keep** | Fine. Add flow-magnitude colouring and per-mode figures. |
| `benchmarks.py` | **keep structure, fix definitions** | Support/load spans do not match the standard MBB/cantilever/L-bracket definitions. Verify each against the reference literature. |
| `graph.py` | **keep, extend** | Add `flow: np.ndarray`, `tree_id`, `area`. Replace dict-of-objects with arrays before you optimize. |
| `pyproject.toml` | keep | Pin versions. |
| `growth.py` | **rewrite** | Replaced by the flow-growth engine (§2.1–2.3). |
| `interactions.py` | **rewrite** | Currently a no-op; needs real planar intersection resolution via `STRtree` + node splitting. |
| `cleaning.py` | **delete, replace with a validator** | Under §2.5 there is nothing to repair; assert `f_e ≠ 0`. |
| `spines.py` | **rewrite** | Spine becomes a conductor with distributed nodes, not two chords. |
| `parameters.py` | **rewrite** | Different parameter set entirely; `anastomosis_radius` and `radius_of_influence` disappear. |
| `forest.py` | **rewrite** | Trivial today; needs seeding without corner degeneracy, plus tree identity. |
| `optimize.py` | **rewrite** | Needs an actual optimizer, determinism, and a two-level structure (§Phase 5–6). |
| `fea.py` | **keep the 6×6 kernel, rewrite everything around it** | `element_stiffness_matrix` is correct. Mesh building, BC/load application, singularity detection, and the zero-load bug all need replacing. |
| `FROND_CONCEPTS.md` | **rewrite** | Documents a CANOPY L-system engine that no longer exists in the code. |
| `implementation_plan.md`, `scratch/` | delete | Superseded. |

---

## Part 5 — Phased plan

**The single most important process change: build the evaluator before the generator.**
You currently have a generator and a broken evaluator, so you cannot tell a good result
from a bad one — which is why tuning has been unproductive.

### Phase 0 — Hygiene (½ day)
`git init`. Seed every RNG and thread the seed through. Delete `scratch/` and
`implementation_plan.md`. Pin dependency versions.

### Phase 1 — Domain, benchmarks, and a *baseline* (2–3 days)
- `Domain` with Γ_s/Γ_l/Γ_d, conductance flags, arc-length parameterization, load-quanta discretization.
- Four benchmarks, each verified against its literature definition: MBB (half-symmetry),
  cantilever, L-bracket, Michell point-loaded cantilever.
- **A working SIMP reference** (top88-style, ~100 lines). Non-negotiable: it is your ground
  truth from day one, and you need it for Part 3 anyway.

### Phase 2 — FE and validation (3–4 days) — *gate*
- Planar intersection resolution: `STRtree` query, split members at crossings, merge
  coincident nodes with a tolerance. Assert zero crossing pairs afterwards.
- Frame FE with: proper Γ_s DOF fixing, distributed Γ_l loading, **a hard error when no node
  reaches the load**, singularity/NaN detection (check the factorization, don't rely on
  `spsolve` raising), and rigid-body-mode detection.
- Verify against a 2-bar truss with hand-computed compliance, and against the SIMP baseline
  on a uniform grid frame. **Do not proceed until this passes.**

### Phase 3 — The flow-growth engine (1–2 weeks)
Implement §2.1–2.4. Sketch of one step:

```
tips = active tips, each carrying (position x, force vector F, tree_id)
while tips:
    for each tip:
        d_support = direction/distance to nearest sink (Γ_s, or Γ_d if conducting)
        candidates = other tips within a search window
        best = argmin over candidates of the Michell merge cost (§2.3)
        if merge cost < solo cost:
            place Steiner point x*; create two members carrying F1, F2;
            new tip carries F1+F2; areas set from |F|/σ
        else:
            advance one step toward d_support (with domain clipping)
        if tip reaches a sink: terminate, record reaction
```
Deliverable: Mode A and Mode B on all four benchmarks, with the assertion `f_e ≠ 0`
holding for every member, and zero unresolved crossings.

### Phase 4 — Cycles and triangulation (1 week)
Multi-support flow splitting; multi-load-case union; buckling-driven bracing (§2.6).
Deliverable: the 2×2 typology table, populated with real figures.

### Phase 5 — Sizing and shape refinement (1–2 weeks) — *this is where the wins are*
A raw generative layout is never competitive; the same is true in the ground-structure
literature. Two cheap gradient stages on a fixed topology:
- **Sizing:** optimality-criteria / fully-stressed iteration on member areas.
- **Shape:** gradient-based refinement of node positions (a few hundred variables — cheap,
  and by far the largest single improvement you will see).

### Phase 6 — Outer loop over growth parameters (1 week)
CMA-ES or Bayesian optimization over the ~10 generative parameters. Because the generator is
stochastic, evaluate each candidate as the mean over R seeded replicates and **report the
variance** — a stochastic generator whose spread is not reported will not survive review.

### Phase 7 — Benchmarking and paper figures (1–2 weeks)
Pareto fronts vs SIMP-skeletonized and vs ground-structure TO at equal volume, same frame FE.
Michell bound where available. Design-variable counts. Mesh-independence study.
Solution-diversity figure. Then rewrite `FROND_CONCEPTS.md` to match the actual method.

---

## Part 6 — Open questions for you

1. **Does the reversed growth direction (load → support) cost you something you care
   about narratively?** It is a strictly better fit for the mechanics, and the root/river
   analogy is arguably stronger, but the canopy image is what CANOPY was built on. A
   bidirectional variant — trees from Γ_s *and* from Γ_l, meeting in the middle, where the
   handshake is exactly where truss diagonals form — preserves both pictures. It is more
   work and I would not start there.

   Comment: Use the reversed growth.

2. **Single load case or multi?** §2.6 argues multi-load-case is the principled route to
   triangulation. If the paper is single-load-case, cycles have to come from multiple
   supports and buckling alone, and the results will be more tree-like.

   Comment: Why not considering all three, multiple support, buckling, and multi-load cases, separately or in combination.

3. **Is FROND a *competitor* to SIMP or a *reparameterization* of TO?** I recommend the
   second framing throughout (Part 3), and it changes how the benchmarks are designed.

   Comment: Personally, I think FROND could produce competing results not only in stiffness but also in mass, at the same time, but I would wait to see the results, be positive, maybe when finally running cases, we can get surprised. My guess is because in FROND the structure is made of thin webs, so hopefully less material for the same  compliance. 



---
Finally, I like the new reformulation you proposed, the mathematical foundations you make reference in the document is quite strong. Lets think on the benchmarks at the end, but definitely not a skeletonized version of a SIMP case. I want direct comparisons. But lets discuss that later.


