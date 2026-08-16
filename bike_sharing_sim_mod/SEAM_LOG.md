# Seam Integration Log

Documenting the integration of RiderBrain into BikeSim.
Purpose: reference material for writing Chapter: (System Architecture & Integration).

## Baseline (before seam)

- Seed: 42, deterministic
- Dataset: population_density_250000_50.json, bike_stations_250000_50.json
- Simulator commit: [git rev-parse HEAD]
- Baseline redirect rates (simple users):
  - none: 0.0%
  - adaptive: 1.9%
  - conservative: 11.8%
  - static: 12.5%
  - dynamic: 14.0%
  - aggressive: 16.2%

## Reconnaissance findings

### best_incentive dictionary structure

Location: bike_sharing_sim_mod/core/Bike-sharing-simulator-v4_AK.py, lines 388-400

Keys:
- `station_id`: destination station ID
- `amount`: [TO CONFIRM — likely raw incentive in €]
- `effective_amount`: amount reduced by distance penalty
- `redirect_distance`: [TO CONFIRM — likely grid units]

### Unit conversions decided

- Distance: 1 grid unit = 133m (calibrated: max_redirection 3.0 units ≈ 400m Fukushige threshold)
- Incentive: passed as-is (assumed € already)
- Weather: environmental (from options.json `is_raining`)
- Urgency: per-trip stochastic (P(urgency)=0.3)

## Design decisions (referenced in Chapter 5)

- Pure RiderBrain decision (no × incentive_attractiveness) — see Design_Decision_RiderBrain_Only.docx
- Legacy bucket logic preserved under `user_model: simple`
- Both modes controlled by single flag in options.json

## Implementation steps

### Step 1: options.json changes
- [ ] Added `experiment.seed` (already done)
- [ ] Added `users.user_model`
- [ ] Added `users.meters_per_unit`
- [ ] Added `users.urgency_prob`
- [ ] Added `environment.is_raining`

### Step 2: simulator changes
- [ ] Import RiderBrain
- [ ] Load model in __init__ (only if realistic mode)
- [ ] Replace acceptance block with if/else on user_model
- [ ] Preserve all post-acceptance logic unchanged

### Step 3: Behavior preservation test
- Run with user_model: simple
- Expected: identical to baseline (deterministic seed guarantees)
- Result: [FILL IN]

### Step 4: First realistic run
- Run with user_model: realistic
- Redirect rates observed: [FILL IN]
- Comparison vs baseline: [FILL IN]

## Notes for Chapter 5 writing

[Add observations, unexpected behavior, design tradeoffs as they arise]

## Notes for Chapter 6 (experiments)

[Comparative results, sensitivity analysis triggers, etc.]