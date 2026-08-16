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

### Why the unit conversion matters

The BikeSim internally uses grid units for spatial distance (redirect_distance ∈ [0, 3.0]).
The RiderBrain was trained on real-world meters (Distance_m ∈ [50, 600]).

These are incompatible unit systems, not just different scales. The conversion factor
`meters_per_unit = 133` is a calibration decision:
- BikeSim's `max_redirection = 3.0` units represents "max acceptable walking distance"
- RiderBrain's `walk_cliff = 400` meters represents Fukushige's exhaustion threshold
- 3.0 × 133 = 400 → the two concepts are aligned

The conversion happens ONLY at the seam boundary, as a local variable, and never
modifies the BikeSim's internal state. The simple mode uses grid units unchanged.

### best_incentive dictionary structure

Location: bike_sharing_sim_mod/core/Bike-sharing-simulator-v4_AK.py, lines 388-400

Keys:
- `station_id`: destination station ID
- `amount`: raw incentive amount in EUROS (€), range ~0.0 - 4.0
- `effective_amount`: amount × (1 - distance_penalty × 0.7), used for sorting
- `redirect_distance`: distance in GRID UNITS (not meters), range 0 - 3.0

### calculate_incentive analysis (lines ~250-310)

Formula: `incentive = max_incentive × shortage_risk × budget_factor × incentive_factor`
- max_incentive = 2 (from options.json)
- Peak values can exceed 2€ when capacity_factor boost applied (× (1 + capacity_factor))
- Absolute cap: station's remaining_budget
- Currency: EUROS, confirmed by simulator prints ($0.97 - $2.83 range per strategy)

### Unit compatibility with RiderBrain training data

| Field | Simulator range | RiderBrain training range | Compatible? |
|---|---|---|---|
| Incentive (€) | 0.0 - 4.0 | 0.5 - 5.0 | Yes (minor extrapolation for <0.5€, expected reject) |
| Distance (m, after 133× conversion) | 0 - 400 | 50 - 600 | Yes, well within range |

### Unit conversions decided

- Distance: 1 grid unit = 133m (calibrated: max_redirection 3.0 units ≈ 400m Fukushige threshold)
- Incentive: passed as-is (already in €)
- Weather: environmental (from options.json `is_raining`)
- Urgency: per-trip stochastic (P(urgency)=0.3 default)

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

## Implementation steps

### Step 1: options.json changes 
- [x] Added `experiment.seed`
- [x] Added `users.user_model` (default: "simple")
- [x] Added `users.meters_per_unit` (default: 133)
- [x] Added `users.urgency_prob` (default: 0.3)
- [x] Added top-level `environment.is_raining` (default: false)

### Step 2: simulator imports 
- [x] Added `import sys`
- [x] Added `sys.path.insert(0, ...)` to expose bike_sharing_sim_mod/ to Python path
- [x] Added `from intelligence.rider_brain import RiderBrain`
- [x] Behavior-preservation test PASSED: baseline numbers identical to pre-import run
- Verified: RiderBrain is now available but not yet used

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