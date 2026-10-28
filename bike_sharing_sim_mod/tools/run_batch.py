"""
Multi-seed batch runner for the simple-vs-realistic comparison.

Runs every combination of  seed x user model x strategy  (plus optional
scenario settings such as rain), each as an independent simulation, and writes
ONE summary row per run to a CSV. Then prints mean and 95% confidence interval
per (user model, strategy).

Nothing in data/options.json is modified: each run gets its own temporary
copy of the options with the requested settings.

Usage (from the simulator_v4 folder):

    python bike_sharing_sim_mod/tools/run_batch.py                       # 50 seeds, both models, all strategies
    python bike_sharing_sim_mod/tools/run_batch.py --seeds 5             # quick test
    python bike_sharing_sim_mod/tools/run_batch.py --rain true --out outputs/batch/rain.csv
    python bike_sharing_sim_mod/tools/run_batch.py --set users.urgency_prob=0.5 --out outputs/batch/urgency05.csv

The run is resumable: if the output CSV already exists, finished runs are skipped.
"""
import argparse
import contextlib
import copy
import csv
import importlib.util
import io
import json
import math
import os
import sys
import tempfile
import time
from multiprocessing import Pool, cpu_count

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))  # bike_sharing_sim_mod/
SIM_FILE = os.path.join(ROOT, 'core', 'Bike-sharing-simulator-v4_AK.py')
OPTIONS_FILE = os.path.join(ROOT, 'data', 'options.json')
GRID_FILE = 'data/population_density_250000_50.json'
STATION_FILE = 'data/bike_stations_250000_50.json'
STRATEGIES = ['none', 'conservative', 'adaptive', 'aggressive', 'dynamic', 'static']

FIELDS = ['seed', 'user_model', 'strategy', 'is_raining', 'overrides', 'days',
          'total_trips', 'redirected_trips', 'redirect_rate', 'total_incentives', 'avg_incentive',
          'cost_per_trip', 'mean_imbalance', 'bike_shortages', 'docking_shortages', 'runtime_s']

_SIM_CLASS = None


def _load_simulator_class():
    """Import BikeSimulator from the hyphenated file name (cached per process)."""
    global _SIM_CLASS
    if _SIM_CLASS is None:
        spec = importlib.util.spec_from_file_location('bikesim_core', SIM_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SIM_CLASS = module.BikeSimulator
    return _SIM_CLASS


def _set_nested(d, dotted_key, value):
    keys = dotted_key.split('.')
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _parse_value(text):
    try:
        return json.loads(text)          # numbers, true/false, lists
    except json.JSONDecodeError:
        return text                      # plain strings


def run_one(job):
    """Run one simulation and return its summary row (executed in a worker process)."""
    seed, user_model, strategy, is_raining, overrides, days, base_options = job
    t0 = time.time()
    os.chdir(ROOT)  # the simulator opens data files with paths relative to this folder

    opts = copy.deepcopy(base_options)
    opts['experiment']['seed'] = seed
    opts['users']['user_model'] = user_model
    opts.setdefault('environment', {})
    opts['environment']['is_raining'] = is_raining
    opts['environment']['debug_realistic'] = False   # never write the debug log in batch runs
    opts['environment']['verbose'] = False
    for key, value in overrides:
        _set_nested(opts, key, value)

    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as tmp:
        json.dump(opts, tmp)
        tmp_path = tmp.name
    try:
        BikeSimulator = _load_simulator_class()
        with contextlib.redirect_stdout(io.StringIO()):   # keep the console quiet
            sim = BikeSimulator(grid_file=GRID_FILE, station_file=STATION_FILE, pref_file=tmp_path)
            sim.preferences['strategies']['mode'] = strategy   # same as the simulator's own main loop
            results = sim.run_simulation(days=days)
            stats = sim.analyze_incentive_effectiveness()['overall_stats']
    finally:
        os.remove(tmp_path)

    hourly = results['hourly_metrics']
    return {
        'seed': seed,
        'user_model': user_model,
        'strategy': strategy,
        'is_raining': is_raining,
        'overrides': ';'.join(f'{k}={v}' for k, v in overrides),
        'days': days,
        'total_trips': stats['total_trips'],
        'redirected_trips': stats['redirected_trips'],
        'redirect_rate': round(stats['redirect_rate'], 6),
        'total_incentives': round(stats['total_incentives'], 4),
        'avg_incentive': round(stats['avg_incentive'], 4),
        'cost_per_trip': round(stats['total_incentives'] / max(1, stats['total_trips']), 6),
        'mean_imbalance': round(float(np.mean([h['imbalance'] for h in hourly])), 6),
        'bike_shortages': int(sum(h['shortage_events'] for h in hourly)),
        'docking_shortages': int(sum(h['docking_shortage_events'] for h in hourly)),
        'runtime_s': round(time.time() - t0, 1),
    }


def _key(row):
    return (int(row['seed']), row['user_model'], row['strategy'],
            str(row['is_raining']).lower() == 'true', row['overrides'], int(row['days']))


def summarize(csv_path):
    """Print mean and 95% CI per (user model, strategy) for the main metrics."""
    import pandas as pd
    df = pd.read_csv(csv_path)
    metrics = ['redirect_rate', 'avg_incentive', 'total_incentives', 'mean_imbalance', 'bike_shortages']
    rows = []
    for (model, strategy), g in df.groupby(['user_model', 'strategy']):
        row = {'user_model': model, 'strategy': strategy, 'n_seeds': len(g)}
        for m in metrics:
            mean, sd = g[m].mean(), g[m].std(ddof=1) if len(g) > 1 else 0.0
            half = 1.96 * sd / math.sqrt(len(g)) if len(g) > 1 else 0.0
            row[m] = mean
            row[m + '_ci95'] = half
        rows.append(row)
    out = pd.DataFrame(rows)
    order = {s: i for i, s in enumerate(STRATEGIES)}
    out = out.sort_values(['user_model', 'strategy'], key=lambda c: c.map(order) if c.name == 'strategy' else c)

    print('\n=== Mean (± 95% CI) across seeds ===')
    for _, r in out.iterrows():
        print(f"{r.user_model:9s} {r.strategy:12s} n={int(r.n_seeds):3d} | "
              f"redirect {100*r.redirect_rate:5.1f}% ±{100*r.redirect_rate_ci95:4.1f} | "
              f"avg €{r.avg_incentive:4.2f} ±{r.avg_incentive_ci95:4.2f} | "
              f"paid €{r.total_incentives:7.0f} ±{r.total_incentives_ci95:5.0f} | "
              f"imbalance {r.mean_imbalance:5.3f} ±{r.mean_imbalance_ci95:5.3f} | "
              f"shortages {r.bike_shortages:6.0f} ±{r.bike_shortages_ci95:4.0f}")
    summary_path = csv_path.replace('.csv', '_summary.csv')
    out.to_csv(summary_path, index=False)
    print(f'\nSummary saved to {summary_path}')

    # How often does each strategy rank first by redirect rate, per model?
    print('\n=== Rank stability: share of seeds where each strategy has the highest redirect rate ===')
    inc = df[df.strategy != 'none']
    for model, g in inc.groupby('user_model'):
        winners = g.loc[g.groupby('seed')['redirect_rate'].idxmax(), 'strategy'].value_counts(normalize=True)
        print(f"{model:9s} " + ', '.join(f"{s} {100*p:.0f}%" for s, p in winners.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seeds', type=int, default=50, help='number of seeds (seeds 1..N); default 50')
    ap.add_argument('--first-seed', type=int, default=1)
    ap.add_argument('--models', nargs='+', default=['simple', 'realistic'])
    ap.add_argument('--strategies', nargs='+', default=STRATEGIES)
    ap.add_argument('--rain', choices=['true', 'false'], default='false')
    ap.add_argument('--days', type=int, default=5, help='simulated days per run (simulator default: 5)')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                    help='override an options.json value, e.g. users.urgency_prob=0.5 (repeatable)')
    ap.add_argument('--workers', type=int, default=max(1, cpu_count() - 1))
    ap.add_argument('--out', default='outputs/batch/batch_results.csv', help='CSV path, relative to bike_sharing_sim_mod/')
    args = ap.parse_args()

    with open(OPTIONS_FILE, encoding='utf-8') as f:
        base_options = json.load(f)
    overrides = []
    for item in args.set:
        key, _, value = item.partition('=')
        overrides.append((key.strip(), _parse_value(value.strip())))
    is_raining = args.rain == 'true'
    override_txt = ';'.join(f'{k}={v}' for k, v in overrides)

    out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = set()
    if os.path.exists(out_path):
        with open(out_path, newline='', encoding='utf-8') as f:
            done = {_key(r) for r in csv.DictReader(f)}

    seeds = range(args.first_seed, args.first_seed + args.seeds)
    jobs = [(s, m, st, is_raining, overrides, args.days, base_options)
            for s in seeds for m in args.models for st in args.strategies
            if (s, m, st, is_raining, override_txt, args.days) not in done]
    total = len(jobs) + len(done)
    print(f'{len(jobs)} runs to do ({len(done)} already in {out_path}), {args.workers} parallel workers')

    new_file = not os.path.exists(out_path)
    t0 = time.time()
    with open(out_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        with Pool(args.workers) as pool:
            for i, row in enumerate(pool.imap_unordered(run_one, jobs), 1):
                writer.writerow(row)
                f.flush()
                elapsed = time.time() - t0
                eta = elapsed / i * (len(jobs) - i)
                print(f'[{len(done) + i}/{total}] seed {row["seed"]:>3} {row["user_model"]:9s} {row["strategy"]:12s} '
                      f'redirect {100*row["redirect_rate"]:5.1f}%  (eta {eta/60:4.1f} min)', flush=True)

    summarize(out_path)


if __name__ == '__main__':
    main()
