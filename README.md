# Contextual and Dynamic Balancing in Smart City Micromobility Systems

MEng Thesis — University of Patras, Department of Computer Engineering & Informatics
Author: **Vasiliki Nasieli** (AM 1090034, up1090034@ac.upatras.gr)
Supervisor: **Andreas Komninos**

---

## Overview

This project extends [BikeSim](https://github.com/komis1/BikeSharingSim) (Komninos et al., 2025) by
replacing its bucket-based user model with a **behaviorally-grounded, context-aware
decision model** grounded in Bounded Rationality (Simon, 1955), willingness-to-walk
thresholds (Fukushige et al., 2022; Sacramento et al., 2022), and environmental
context (Kim, 2018).

The central research question is one of **robustness**:

> *Do the systemic conclusions of BikeSim about the relative cost-efficiency of
> incentive strategies still hold when its homogeneous, static user typology is
> replaced with a behaviorally-realistic, context-aware decision model?*

The main methodological contribution is not the ML model itself (which serves as a
fast surrogate of a literature-calibrated utility function), but the **comparative
experiment** it enables: running the same simulator, with the same seeds and
scenarios, under two different user decision layers.

---

## Repository structure

```
simulator_v4/
└── bike_sharing_sim_mod/           ← project root
    ├── main.py                     ← entry point
    ├── core/
    │   └── Bike-sharing-simulator-v4_AK.py   ← BikeSim (refactored, with seam)
    ├── data/
    │   ├── generate_dataset.py     ← Monte Carlo synthetic behavioral data
    │   ├── synthetic_dataset.csv   ← generated training set (10,000 records)
    │   ├── options.json            ← simulation configuration (all knobs)
    │   ├── bike_stations_*.json
    │   └── population_density_*.json
    ├── intelligence/
    │   ├── train_ai.py             ← XGBoost training pipeline
    │   ├── rider_brain.py          ← model wrapper: RiderBrain.decide(...)
    │   └── xgboost_model.pkl       ← trained surrogate (~94% accuracy)
    ├── tools/
    │   ├── grid_generator.py       ← urban grid setup (from BikeSim)
    │   └── analyze_debug.py        ← analysis script for debug CSV logs
    ├── outputs/
    │   ├── baseline_simple/        ← reference metrics under simple user model
    │   └── (per-run metrics, gitignored)
    └── notebooks/
        └── metrics.ipynb           ← exploratory analysis
```

---

## Key changes to the original BikeSim

The extension preserves the original simulator's behavior by default. All modifications
sit behind explicit configuration flags:

| Component | Change | Location |
|---|---|---|
| Deterministic execution | Added `experiment.seed` to `options.json`; simulator reseeds `random` and `np.random` on every `__init__` | `Bike-sharing-simulator-v4_AK.py` (start of `__init__`) |
| User model selection | `user_model: simple \| realistic` flag switches between the original bucket logic and the RiderBrain-based decision | `options.json` (`users` block) and the seam in `generate_trips` |
| Distance unit conversion | Grid units → meters (via `meters_per_unit`) only at the seam boundary; core simulator remains in grid units | Seam in `generate_trips` |
| Environmental context | `is_raining` (system-level) + per-trip stochastic `urgency` (probability `urgency_prob`) | `options.json` (`environment` block), consumed only in realistic mode |
| Debug logging | Optional CSV logging of every decision fed to the RiderBrain (feature values + returned probability), toggled by `environment.debug_realistic` | `outputs/debug_realistic_decisions.csv` |

**The original bucket-based decision logic is not deleted** , it remains as the
`simple` branch of the seam. This enables a strict behavior-preservation test:
setting `user_model: simple` reproduces the pre-modification baseline exactly (to
the last decimal), given the same seed.

---

## Quick start

Run all six incentive strategies (none / conservative / adaptive / aggressive / dynamic / static)
under the currently configured user model:

```bash
python bike_sharing_sim_mod/main.py
```

The simulator writes per-strategy metrics to `bike_sharing_sim_mod/outputs/`. With the
default configuration (seed=42, `user_model: simple`) the outputs are deterministic
and reproduce the values captured in `outputs/baseline_simple/`.

To run with the behaviorally-realistic user model, edit `options.json`:

```json
"users": {
    "user_model": "realistic",
    ...
}
```

To enable per-decision logging for diagnostic analysis:

```json
"environment": {
    "is_raining": false,
    "debug_realistic": true
}
```

then run the analysis script:

```bash
python bike_sharing_sim_mod/tools/analyze_debug.py
```

---

## Reproducibility

Every run is deterministic given a fixed seed. The simulator is stochastic in behavior
(user categories, destination sampling, initial bike distributions, acceptance draws
all remain random variables) but reproducible in execution: with `experiment.seed: 42`,
every run produces byte-identical metrics files.

The baseline metrics under `outputs/baseline_simple/` correspond to seed=42 with the
original bucket-based user model.

For statistical claims in the thesis, results are aggregated across multiple seeds
(seeds 42, 123, 456, 789, 1000) and reported as mean ± standard deviation. See
`outputs/multi_seed/` (populated during the Week 2 validation phase of the thesis
workplan).

---

## Behavioral calibration

The synthetic dataset is generated from a Logit utility function whose *functional
forms* are drawn from published literature, while the *coefficient magnitudes* are
selected to produce qualitatively consistent behavior with reported findings.
Sensitivity of downstream conclusions to these coefficients is assessed as part of
the thesis experimental design.

| Element | Functional form (literature) | Coefficient magnitude (calibrated) |
|---|---|---|
| Distance threshold | Sharp acceptance drop near ~400m (Fukushige et al., 2022; Sacramento et al., 2022) | Cliff penalty magnitude |
| Monetary incentive | Diminishing marginal utility (logarithmic) | Scale coefficient (`2 × log`) |
| Weather | Direction & significance of effect (Kim, 2018) | Penalty weight (−1.5) |
| Urgency | Order of magnitude of acceptance reduction | Coefficient (−2.0) |
| Stochasticity | Satisficing over optimization (Simon, 1955) | Noise σ (0.5) |

All coefficients are exposed as parameters of `generate_dataset()`, enabling
sensitivity re-runs without code changes.

---

## Attribution

This work builds directly on:

> Komninos, A., et al. (2025). *BikeSim: A discrete-event simulator for evaluating
> adaptive incentive strategies in bike-sharing systems.* IEEE Smart Cities.
> Source: https://github.com/komis1/BikeSharingSim

The BikeSim core (station dynamics, incentive strategies, demand generation) is
preserved as-is under the `simple` user model. The behavioral decision layer, the
seam that enables user-model switching, the deterministic-seed infrastructure, and
the accompanying analysis tooling are original contributions of this thesis.

---

## Status

**Current phase:** Verification and sensitivity analysis (Aug 2026).
**Expected completion:** October 2026.

This repository is under active development. Interfaces and file layouts may change
until thesis submission.
