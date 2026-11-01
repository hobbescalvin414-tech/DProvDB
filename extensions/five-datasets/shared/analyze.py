#!/usr/bin/env python3
"""Validate the complete factorial design, then create dataset-local statistics and figures."""
import csv, gzip, hashlib, itertools, json, math, pathlib, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parents[3];BASE=ROOT/'extensions/five-datasets'
METHODS=['aGM','baseline','PrivateSQL','Chorus','ChorusP']
LABEL={'aGM':'DProvDB/aGM','baseline':'Vanilla','PrivateSQL':'sPrivateSQL','Chorus':'Chorus','ChorusP':'ChorusP'}
COLOR=dict(zip(METHODS,['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00']))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(name):
 folder=BASE/name;m=json.loads((folder/'manifest.json').read_text());df=pd.read_csv(folder/'raw/results.csv')
 expected=set(itertools.product(['RRQ'],METHODS,['round-robin','random'],[.4,.8,1.6,3.2,6.4],range(1,5)))|set(itertools.product(['BFS'],['aGM','baseline','Chorus','ChorusP'],['BFS'],[200.],range(1,5)))
 observed=list(df[['phase','mechanism','scheduler','budget','run']].itertuples(index=False,name=None))
 assert len(df)==216 and len(set(observed))==216 and set(observed)==expected
 assert (df.dataset==name).all() and (df.seed==df.run*1025).all()
 assert (df.utility==df.answered_low+df.answered_high).all()
 assert (df.utility==df.noncached+df.cache_hits).all()
 assert (df.utility.between(0,df.candidate_queries)).all()
 assert (df.loc[df.phase=='RRQ','candidate_queries']==8000).all()
 assert (df.loc[df.phase=='BFS','candidate_queries']==312).all()
 assert (df.per_query_delta==1e-9).all() and (df.total_delta==1e-5).all()
 assert np.isfinite(df[['epsilon','epsilon_low','epsilon_high','execution_ms','dcfg']]).all().all()
 assert (df.epsilon>=0).all() and (df.epsilon<=df.budget+1e-6).all()
 assert (df.noncached*df.per_query_delta<=df.total_delta).all()
 expected_dcfg=df.answered_low+df.answered_high/math.log2(1.25)
 assert np.allclose(df.dcfg,expected_dcfg,rtol=1e-10,atol=1e-8)
 positive=df.utility>0
 assert np.allclose(df.loc[positive,'ndcfg'],(expected_dcfg/df.utility)[positive])
 assert df.loc[~positive,'ndcfg'].isna().all() and df.loc[~positive,'requested_variance_mean'].isna().all()
 assert df.loc[positive,'ndcfg'].between(1-1e-9,1/math.log2(1.25)+1e-9).all()
 hist=pd.read_csv(folder/'raw/histograms.csv')
 assert len(hist)==250 and not hist.duplicated(['attribute','bin']).any()
 assert (hist.groupby('attribute')['count'].sum()==m['raw_rows']).all()
 for _,group in hist.groupby('attribute'):assert set(group.bin)==set(range(50))
 logpath=folder/'logs/formal.log.gz'
 if logpath.exists():
  log=gzip.open(logpath,'rt').read()
 else:log=(folder/'raw.log').read_text()
 assert log.count('EXTENSION_COMPLETE ')==216
 assert f'EXTENSION_SUCCESS dataset={name} records=216' in log
 assert 'Exception in thread' not in log
 validation=dict(passed=True,records=216,rrq_records=200,bfs_records=16,repeats=4,unique_configurations_without_repeat=54,seeds=[1025,2050,3075,4100],zero_utility_records=int((~positive).sum()),ndcfg_undefined_records=int(df.ndcfg.isna().sum()),histogram_rows=int(len(hist)),data_rows=m['raw_rows'],observed_global_epsilon_within_budget=True,agm_low_quota_exceedances=int(((df.mechanism=='aGM')&(df.epsilon_low>df.budget/4+1e-6)).sum()),note='Implementation accounting consistency, not a differential privacy proof; individual quotas are NOT claimed to pass.',result_sha256=sha(folder/'raw/results.csv'),histogram_sha256=sha(folder/'raw/histograms.csv'))
 (folder/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 return df,m,hist

def aggregate(df):
 metrics=['utility','ndcfg','epsilon','cache_hits','noncached','requested_variance_mean','execution_ms','answered_low','answered_high']
 out=df.groupby(['phase','scheduler','budget','mechanism'])[metrics].agg(['mean','std','count'])
 out.columns=['_'.join(c) for c in out.columns]
 return out.reset_index()
def plot(name,df,hist):
 dest=BASE/name/'figures';dest.mkdir(exist_ok=True)
 rr=df[df.phase=='RRQ']
 for metric,title,ylabel in [('utility','Answered range queries','Answered queries (of 8,000)'),('ndcfg','Normalized DCFG (undefined when zero answers)','nDCFG (not a 0-1 score)')]:
  fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
  for ax,sched in zip(axes,['round-robin','random']):
   for method in METHODS:
    s=rr[(rr.scheduler==sched)&(rr.mechanism==method)].groupby('budget')[metric].agg(['mean','std'])
    ax.errorbar(s.index,s['mean'],yerr=s['std'],marker='o',markersize=4,capsize=3,label=LABEL[method],color=COLOR[method])
   ax.set_xscale('log',base=2);ax.set_xticks([.4,.8,1.6,3.2,6.4],labels=['0.4','0.8','1.6','3.2','6.4']);ax.set_xlabel('Total epsilon budget');ax.set_title(sched);ax.grid(alpha=.2)
  axes[0].set_ylabel(ylabel);axes[1].legend(fontsize=8);fig.suptitle(name+': '+title+('; 4 runs, undefined omitted' if metric=='ndcfg' else '; mean +/- sample SD, n=4'),fontsize=11);fig.tight_layout();fig.savefig(dest/(metric+'.png'));plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 bfs=df[df.phase=='BFS'];methods=['aGM','baseline','Chorus','ChorusP'];x=np.arange(4)
 s=bfs.groupby('mechanism').agg(answers=('utility','mean'),sd=('utility','std'),cache=('cache_hits','mean'),eps=('epsilon','mean'),eps_sd=('epsilon','std')).reindex(methods)
 axes[0].bar(x,s['answers'],yerr=s['sd'],capsize=4,color=[COLOR[k] for k in methods],alpha=.85,label='All answers')
 axes[0].bar(x,s['cache'],color='none',edgecolor='black',hatch='///',label='Cache hits (part of total)');axes[0].set_ylim(0,335);axes[0].set_ylabel('Answered queries (maximum tree: 312)');axes[0].legend(fontsize=8)
 axes[1].bar(x,s['eps'],yerr=s['eps_sd'],capsize=4,color=[COLOR[k] for k in methods]);axes[1].set_ylabel('Final implementation epsilon ledger')
 for ax in axes:ax.set_xticks(x,labels=[LABEL[k] for k in methods],rotation=15);ax.grid(axis='y',alpha=.2)
 fig.suptitle(name+': BFS; budget=200; mean +/- sample SD, n=4');fig.tight_layout();fig.savefig(dest/'bfs.png');plt.close(fig)
 fig,axes=plt.subplots(3,2,figsize=(10,8))
 for ax,(attr,group) in zip(axes.flat,hist.groupby('attribute',sort=False)):
  group=group.sort_values('bin');ax.bar(group.bin*20,group['count']/group['count'].sum()*100,width=20,align='edge',color='#0072B2');ax.set_title(attr,fontsize=10);ax.set_xlabel('Scaled field value');ax.set_ylabel('% of all records')
 axes.flat[-1].axis('off');fig.suptitle(name+': full-data distributions, 50 equal-width bins');fig.tight_layout();fig.savefig(dest/'distribution.png');plt.close(fig)

def main():
 names=sys.argv[1:] or ['bank','credit','shoppers','diabetes','covertype'];allframes=[]
 for name in names:
  df,m,hist=verify(name);summary=aggregate(df);summary.to_csv(BASE/name/'summary.csv',index=False,float_format='%.10g');plot(name,df,hist);allframes.append(df);print(name,'216 configurations validated',flush=True)
 if len(names)==5:
  freeze=json.loads((BASE/'shared/experiment.json').read_text())
  for path,digest in freeze['source_sha256'].items():assert sha(ROOT/path)==digest,('source changed',path)
  reference=allframes[0].query("phase == 'RRQ'").sort_values(['mechanism','scheduler','budget','run'])
  compare=['utility','answered_low','answered_high','dcfg','epsilon','epsilon_low','epsilon_high','cache_hits','noncached','requested_variance_mean']
  equal={name: bool(np.allclose(reference[compare].to_numpy(),df.query("phase == 'RRQ'").sort_values(['mechanism','scheduler','budget','run'])[compare].to_numpy(),equal_nan=True)) for name,df in zip(names,allframes)}
  (BASE/'shared/validation.json').write_text(json.dumps(dict(passed=True,total_records=1080,source_hashes_unchanged=True,rrq_accounting_identical_to_first_dataset=equal,datasets=names),indent=2)+'\n')
if __name__=='__main__':main()
