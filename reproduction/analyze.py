"""Validate completed experiment CSVs and generate figures from measured data."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

NAMES = {'aGM': 'DProvDB', 'baseline': 'Vanilla', 'PrivateSQL': 'sPrivateSQL',
         'Chorus': 'Chorus', 'ChorusP': 'ChorusP'}
COLORS = dict(zip(NAMES.values(), ['#176B87', '#D78521', '#7C5BA7', '#AC4055', '#608B52']))
EXPECTED = {'EQW_{d}_end_to_end': 16, 'RRQ_{d}_end_to_end': 200,
            'RRQ_{d}_analyst_constraints': 108, 'RRQ_{d}_increasing_workload': 480,
            'RRQ_{d}_fairness': 160, 'RRQ_{d}_compositions': 12}


def number_list(value):
    return [float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', str(value))]


def load(path):
    frame = pd.read_csv(path, sep=';', skipinitialspace=True)
    frame.columns = frame.columns.str.strip()
    for col in frame.select_dtypes('object'):
        frame[col] = frame[col].str.strip()
    frame['method'] = frame.mechanism.map(NAMES)
    frame['ndcfg'] = frame.DCFG / frame.utility.replace(0, np.nan)
    frame['budget_used'] = frame.accountant.map(lambda x: number_list(x)[-1] if number_list(x) else np.nan)
    frame['analysts'] = frame.analystConstraints.map(lambda x: len(number_list(x)))
    frame['per_query_ms'] = frame.execution_time / frame.utility.replace(0, np.nan)
    frame['variant'] = frame.viewConstraintFlag
    return frame


def curves(ax, frame, x, y='utility', label_column='method'):
    for name, group in frame.groupby(label_column, sort=False):
        g = group.groupby(x)[y].agg(['mean', 'std']).sort_index()
        ax.errorbar(g.index, g['mean'], yerr=g['std'].fillna(0), label=name,
                    color=COLORS.get(name), marker='o', markersize=3, capsize=2, linewidth=1.6)
    ax.set_xlabel(x)
    ax.set_ylabel({'utility': 'Answered queries', 'ndcfg': 'nDCFG', 'budget_used': 'Consumed privacy budget'}.get(y, y))
    ax.grid(alpha=.2)


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    root = args.results
    tables = root / 'tables'
    figures = root / 'figures'
    tables.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    expected = {key.format(d=d): n for d in ('adult', 'tpch') for key, n in EXPECTED.items()}
    expected['RRQ_adult_end_to_end_delta'] = 200
    actual = {p.stem for p in (root / 'raw').glob('*.csv')}
    assert actual == set(expected), {'missing': sorted(set(expected) - actual),
                                     'unexpected': sorted(actual - set(expected))}
    frames = {}
    issues = []
    validation = []
    for stem, rows in expected.items():
        path = root / 'raw' / (stem + '.csv')
        f = load(path)
        assert len(f) == rows, (stem, len(f), rows)
        assert set(f.runIndex) == {1, 2, 3, 4}, stem
        assert set(f.randomness) == {1025, 2050, 3075, 4100}, stem
        assert (f.randomness == f.runIndex * 1025).all(), stem
        assert set(f.dataset) == {stem.split('_')[1]}, stem
        assert f.method.notna().all(), stem
        assert (f.utility >= 0).all() and (f.utility <= f.totalNoOfQueries).all(), stem
        assert np.isfinite(f[['utility', 'execution_time', 'setup_time', 'DCFG']]).all().all(), stem
        assert (f[['execution_time', 'setup_time', 'DCFG']] >= 0).all().all(), stem
        assert np.isfinite(f.budget_used).all() and (f.budget_used >= 0).all(), stem
        # Raw DCFG is unnormalized; utility=0 correctly produces undefined nDCFG.
        assert (f.utility_breakdown.map(lambda v: sum(number_list(v))) == f.utility).all(), stem
        assert (f.utility_breakdown.map(lambda v: len(number_list(v))) == f.analysts).all(), stem
        over = int((f.budget_used > f.budget + 1e-6).sum())
        if over:
            issues.append(f'{stem}: {over} rows exceed reported epsilon budget')
        frames[stem] = f
        validation.append({'file': path.name, 'rows': len(f), 'expected_rows': rows,
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'epsilon_exceeded_rows': over})
        keys = ['method', 'task', 'budget', 'variant', 'totalNoOfQueries', 'analysts', 'perQueryDelta']
        # Composition name is not emitted by upstream CSV: infer only from the
        # documented inner-loop order, three rows for each run.
        if stem.endswith('_compositions'):
            assert f.runIndex.tolist() == [run for run in range(1, 5) for _ in range(3)], stem
            f['composition'] = ['basic', 'advanced', 'renyi'] * 4
            keys.append('composition')
        grouped = f.groupby(keys, dropna=False)
        sizes = grouped.size()
        assert (sizes == 4).all(), (stem, sizes.to_dict())
        assert (grouped.runIndex.nunique() == 4).all(), stem
        summary = grouped.agg(n=('utility', 'size'), utility_mean=('utility', 'mean'),
            utility_sd=('utility', 'std'), ndcfg_mean=('ndcfg', 'mean'),
            ndcfg_sd=('ndcfg', 'std'), ndcfg_n=('ndcfg', 'count'), budget_mean=('budget_used', 'mean'),
            budget_sd=('budget_used', 'std'), setup_ms=('setup_time', 'mean'),
            execution_ms=('execution_time', 'mean'), per_query_ms=('per_query_ms', 'mean')).reset_index()
        summary.to_csv(tables / (stem + '.csv'), index=False)

    for d in ('adult', 'tpch'):
        f = frames[f'RRQ_{d}_end_to_end']
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.5))
        for ax, scheduler in zip(axs, ('RRQ_round-robin', 'RRQ_random')):
            curves(ax, f[f.task == scheduler], 'budget')
            ax.set_xlabel('Overall epsilon')
            ax.set_title(f'{d.upper()} / {scheduler.removeprefix("RRQ_")}')
        axs[0].legend(fontsize=9)
        save(fig, figures / f'{d}_utility.png')
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.5))
        for ax, scheduler in zip(axs, ('RRQ_round-robin', 'RRQ_random')):
            curves(ax, f[f.task == scheduler], 'budget', 'ndcfg')
            ax.set_xlabel('Overall epsilon')
            ax.set_title(scheduler.removeprefix('RRQ_'))
        axs[0].legend(fontsize=9)
        save(fig, figures / f'{d}_fairness.png')

        f = frames[f'RRQ_{d}_analyst_constraints'].copy()
        f['configuration'] = np.where(f.mechanism == 'baseline', 'Vanilla (sum)',
            np.where(f.variant.str.contains('fixed-aGM'), 'DProvDB (max)', 'DProvDB (sum)'))
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.5))
        curves(axs[0], f[f.budget == 3.2], 'analysts', label_column='configuration')
        curves(axs[1], f[f.analysts == 2], 'budget', label_column='configuration')
        axs[0].set_xlabel('Number of analysts')
        axs[1].set_xlabel('Overall epsilon')
        axs[0].legend(fontsize=9)
        save(fig, figures / f'{d}_analysts.png')

        f = frames[f'RRQ_{d}_increasing_workload']
        fig, grid = plt.subplots(2, 3, figsize=(10, 5.8))
        axs = grid.ravel()
        for ax, epsilon in zip(axs, (.4, .8, 1.6, 3.2, 6.4)):
            curves(ax, f[f.budget == epsilon], 'totalNoOfQueries')
            ax.set_title(f'epsilon={epsilon}')
            ax.set_xlabel('Submitted queries')
            ax.ticklabel_format(axis='x', style='sci', scilimits=(0, 0))
        axs[0].legend(fontsize=8)
        axs[-1].axis('off')
        save(fig, figures / f'{d}_cache.png')

        f = frames[f'RRQ_{d}_fairness'].copy()
        f['expansion'] = f.variant.str.extract(r':\s*([\d.]+)').astype(float)
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.5))
        for ax, metric in zip(axs, ('utility', 'ndcfg')):
            sub = f[f.task == 'RRQ_round-robin'].copy()
            sub['epsilon'] = sub.budget.map(lambda v: f'epsilon={v:g}')
            curves(ax, sub, 'expansion', metric, 'epsilon')
            ax.set_title('round-robin')
        axs[0].legend(fontsize=9)
        save(fig, figures / f'{d}_expansion.png')

    fig, axs = plt.subplots(1, 2, figsize=(10, 3.5))
    bfs_summary = []
    for ax, d in zip(axs, ('adult', 'tpch')):
        f = frames[f'EQW_{d}_end_to_end']
        g = f.groupby('method').agg(budget_mean=('budget_used', 'mean'), budget_sd=('budget_used', 'std'),
            queries=('utility', 'mean'), execution_ms=('execution_time', 'mean'), setup_ms=('setup_time', 'mean'))
        g['dataset'] = d
        bfs_summary.append(g.reset_index())
        ax.bar(g.index, g.budget_mean, yerr=g.budget_sd, color=[COLORS[x] for x in g.index], capsize=3)
        ax.set_title(d.upper() + ' / BFS')
        ax.set_ylabel('Last recorded epsilon')
        ax.tick_params(axis='x', rotation=25)
    save(fig, figures / 'bfs_budget.png')
    pd.concat(bfs_summary).to_csv(tables / 'bfs_summary.csv', index=False)

    f = frames['RRQ_adult_end_to_end_delta']
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.5))
    for ax, task in zip(axs, ('RRQ_round-robin', 'RRQ_random')):
        curves(ax, f[f.task == task], 'perQueryDelta')
        ax.set_xscale('log')
        ax.set_xlabel('Per-query delta')
        ax.set_title('Adult / ' + task.removeprefix('RRQ_'))
    axs[0].legend(fontsize=9)
    save(fig, figures / 'adult_delta.png')
    metrics = {'datasets': {}, 'rows': sum(len(f) for f in frames.values()), 'issues': issues}
    for d in ('adult', 'tpch'):
        e2e = frames[f'RRQ_{d}_end_to_end'].groupby(['task','budget','method']).utility.mean().unstack()
        agm = frames[f'RRQ_{d}_analyst_constraints']
        six = agm[(agm.analysts == 6) & (agm.budget == 3.2)]
        best = six[(six.mechanism == 'aGM') & six.variant.str.contains('fixed-aGM')].utility.mean()
        base = six[six.mechanism == 'baseline'].utility.mean()
        metrics['datasets'][d] = {
            'e2e_agm_at_least_vanilla': int((e2e.DProvDB >= e2e.Vanilla).sum()),
            'e2e_settings': len(e2e),
            'six_analysts_agm': float(best), 'six_analysts_vanilla': float(base),
            'six_analysts_ratio': float(best/base) if base else None,
            'epsilon_6_4_round_robin': e2e.loc[('RRQ_round-robin', 6.4)].to_dict()}
    (root / 'validation.json').write_text(json.dumps({'files': validation, 'issues': issues}, indent=2))
    (root / 'summary.json').write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
