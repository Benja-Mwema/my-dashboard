"""Versioned WS30 transfers. No MT5 order/account calls. Separate detection/scoring."""
from pathlib import Path
import json, hashlib, importlib.util, inspect, types, argparse, zipfile, sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
ho=module('frozen_h01',ROOT/'frozen/h01/run_scan.py')
relax=module('frozen_c1',ROOT/'frozen/c1/relaxation.py');base=relax.base;be=relax.be
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def menu():
 result=[]
 defs={'H01':[{}, {'depth':.75},{'depth':1.25},{'band':.35},{'band':.75},{'defense':6,'resume':3},{'defense':12,'resume':6}],
       'C1':[{}, {'second_window':16},{'second_window':32},{'floor_tolerance':.1},{'floor_tolerance':.2},{'accept_clearance':.1},{'accept_clearance':.2}],
       'Combined':[{}, {'weeks':3},{'weeks':6},{'f1_tolerance':.1},{'r4_close':True}],
       'D04':[{}, {'zone':.25},{'zone':.75},{'retest_window':4},{'retest_window':12},{'bearish':True},{'close_clearance':.1}]}
 for family,changes in defs.items():
  for i,c in enumerate(changes):result.append({'family':family,'id':family+('_BASE' if i==0 else '_A'+str(i)),'changes':c})
 assert len(result)==26
 return result

def load_frames(folder):
 f={}
 for tf,mins in [('M1',1),('M15',15),('H1',60),('H4',240),('D1',1440),('W1',10080)]:
  d=pd.read_csv(folder/(tf+'.csv'));d=d[d.confirmed_by_later_bar.eq(1)].copy()
  d['t']=pd.to_datetime(d.broker_time);d['end']=d.t+pd.Timedelta(minutes=mins)
  if tf in ['H1','H4']:d=d[d.t>='2026-01-01']
  d=d.reset_index(drop=True);assert d.t.is_unique and d.t.is_monotonic_increasing
  if tf in ['H1','H4']:
   tr=pd.concat([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()],axis=1).max(axis=1)
   d['A']=base.wilder(tr);d['atr14']=d.A
  f[tf]=d
 h=f['H1'];ref=f['D1'][['t','end','high','low']].rename(columns={'t':'ref_day','end':'ref_known','high':'ref_high','low':'ref_low'})
 h=pd.merge_asof(h,ref,left_on='t',right_on='ref_known',direction='backward');h['R']=h.ref_high;h['idx']=np.arange(len(h));f['H1']=h
 return f

def audit_frames(f):
 details=[];bad={}
 for tf,freq in [('H1','h'),('M15','15min')]:
  agg=f['M1'].groupby(f['M1'].t.dt.floor(freq)).agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),tick_volume=('tick_volume','sum'))
  q=f[tf].set_index('t').join(agg,rsuffix='_m1');mask=q.open_m1.isna()
  for c in ['open','high','low','close','tick_volume']:mask|=(q[c]-q[c+'_m1']).abs()>1e-7
  bad[tf]=set(q.index[mask]);z=q[mask].reset_index();z['timeframe']=tf;details.extend(z.to_dict('records'))
 return bad,details

def h01(f,c):
 # Preserve original admission and reservation code. Only declared constants vary.
 source=inspect.getsource(ho.Scan)
 pairs=[("if e['depth_A']<1:","if e['depth_A']<"+str(c.get('depth',1))+":"),
        ('<=.5*A','<='+str(c.get('band',.5))+'*A'),
        ('rc+9','rc+'+str(c.get('defense',8)+1)),('rc+8','rc+'+str(c.get('defense',8))),
        ('k-hold<=4','k-hold<='+str(c.get('resume',4))),('k-hold==4','k-hold=='+str(c.get('resume',4)))]
 for a,b in pairs:assert a in source;source=source.replace(a,b)
 ns=dict(ho.__dict__);exec(compile(source,'h01_declared_variant','exec'),ns)
 class Scanner(ns['Scan']):
  def __init__(self,frames):
   self.f=frames;self.h=frames['H1'];self.m=frames['M1'];self.m15=frames['M15'];self.n=len(self.h)
   self.ht=self.h.t.to_numpy();self.mt=self.m.t.to_numpy();self.m15t=self.m15.t.to_numpy();self.cutoff=self.h.end.iloc[-1]
   self.stages=[];self.episodes=[];self.breaches=[];self.trades=[]
  def outcome(self,e,policy,k):
   entry=self.next_entry(k);o={'episode_id':e['episode_id'],'policy':policy,'direction':e['direction'],'signal_idx':k,'signal_time':str(self.h.end.iloc[k]),'A':e['A'],'reference':e['reference'],'seed_time':e['break_time']}
   if entry is None:o.update(entry_time='',horizon_end='',status='censored',score=np.nan);return o,pd.Timestamp.max
   j=int(np.searchsorted(self.ht,np.datetime64(entry.t)));last=j+23;complete=last<self.n;end=self.h.end.iloc[last] if complete else pd.Timestamp.max
   o.update(entry_time=str(entry.t),entry=float(entry.open),horizon_end=str(end) if complete else '',status='unscored' if complete else 'censored',score=0.)
   return o,end
 sc=Scanner(f);ep,tr,br,st=sc.run();selected=[]
 if len(tr):
  em=ep.set_index('episode_id')
  for r in tr[tr.policy.eq('H')].to_dict('records'):
   e=em.loc[r['episode_id']];s=int(e.sign);a=int(f['H1'].end.searchsorted(pd.Timestamp(e.defense_time)));k=r['signal_idx']
   if (s*(f['H1'].close.iloc[a+1:k+1]-e.defense_extreme)<0).any():continue
   selected.append({**{key:r[key] for key in ['episode_id','direction','signal_idx','signal_time','A','reference','seed_time']},'branch':'H01','defense':float(e.defense_extreme),'sign':s,'signal_key':r['episode_id']+'@'+str(k)})
 return selected,ep.to_dict('records')

def c1scan(h,seeds,c,branch='C1'):
 v={**relax.DEFAULT,'id':branch}
 if branch=='C1':v.update(defense=False,floor_mode='close',accept='close')
 else:v.update(secondary_floor=False)
 v.update(c)
 src=inspect.getsource(relax.scan)
 src=src.replace("float(fr[v['floor_mode']])<=B","float(fr[v['floor_mode']])<=B-v.get('floor_tolerance',0)*float(fr.A)")
 src=src.replace("float(r[v['floor_mode']])<=B","float(r[v['floor_mode']])<=B-v.get('floor_tolerance',0)*float(fr.A)")
 src=src.replace("float(r[v['floor_mode']])<=P","float(r[v['floor_mode']])<=P-v.get('floor_tolerance',0)*float(fr.A)")
 src=src.replace("float(h.iloc[k][v['accept']])>Q","float(h.iloc[k][v['accept']])>Q+v.get('accept_clearance',0)*float(h.iloc[k].A)")
 ns=dict(relax.__dict__);exec(compile(src,'c1_declared_variant','exec'),ns)
 return ns['scan'](h,seeds,v)

def detect(f,v):
 family=v['family'];c=v['changes'];h=f['H1'];n=len(h)
 if family=='H01':return h01(f,c)
 seeds=base.detect(h)['first']
 if family=='C1':
  ss,ledger=c1scan(h,seeds,c);return [{**s,'sign':1,'branch':'C1'} for s in ss],ledger
 events=[];ledger=[]
 if family=='Combined':
  ss,cl=c1scan(h,seeds,{});events.extend({**s,'branch':'C1','priority':0,'sign':1} for s in ss);ledger.extend(cl)
  rr,rl=c1scan(h,seeds,{'accept':'close'} if c.get('r4_close') else {},'R4');events.extend({**s,'branch':'R4','priority':3,'sign':1} for s in rr);ledger.extend(rl)
  for seed in seeds:
   i=int(seed['signal_idx']);k=i+1
   if k>=n:continue
   b=h.iloc[i];r=h.iloc[k];R=seed['R'];tol=c.get('f1_tolerance',0)
   passes=r.low>R if not tol else (r.low>R-tol*b.A and r.close>R+tol*b.A)
   if not passes:continue
   d=f['D1'];ref=d[d.t.eq(b.ref_day)]
   if not len(ref):continue
   w=f['W1'][f['W1'].end<=b.ref_day].tail(c.get('weeks',4));weekly=len(w)==c.get('weeks',4) and ref.close.iloc[0]>w.high.max()
   inside=r.high<=b.high and r.low>b.low and r.close>=b.close
   if weekly or inside:events.append({**seed,'signal_idx':k,'signal_time':str(r.end),'signal_key':seed['episode_id']+'@'+str(k),'branch':'F1W4' if weekly else 'F1_PRICE','priority':1 if weekly else 2,'sign':1})
 elif family=='D04':
  for seed in seeds:
   i=int(seed['signal_idx']);B=seed['B'];fail=None
   for k in range(i+1,min(n,i+25)):
    if h.iloc[k].close<B:fail=k;break
   if fail is None:ledger.append({**seed,'stage':'no_floor_failure'});continue
   fr=h.iloc[fail];Af=float(fr.A);Z=B-c.get('zone',.5)*Af
   common={**seed,'sign':-1,'failure_idx':fail,'failure_ATR':Af,'zone_level':Z}
   if fail+1<n and h.iloc[fail+1].high<B:
    k=fail+1;events.append({**common,'signal_idx':k,'signal_time':str(h.iloc[k].end),'signal_key':seed['episode_id']+'@'+str(k)+':SELL','branch':'ORIGINAL','priority':0})
   found=None
   for k in range(fail+1,min(n,fail+c.get('retest_window',8)+1)):
    r=h.iloc[k];p=h.iloc[k-1]
    if p.close<Z and r.high>=Z and r.close<Z:found=k;break
   if found is not None:
    r=h.iloc[found];passed=(not c.get('bearish') or r.close<r.open) and (r.close<Z-c.get('close_clearance',0)*Af)
    ledger.append({**common,'retest_idx':found,'stage':'early_signal' if passed else 'first_retest_guard_rejected'})
    if passed:events.append({**common,'signal_idx':found,'signal_time':str(r.end),'signal_key':seed['episode_id']+'@'+str(found)+':SELL','branch':'EARLIER','priority':1})
 else:raise ValueError(family)
 seen=set();selected=[]
 for r in sorted(events,key=lambda r:(r['signal_time'],r['priority'],r['episode_id'])):
  if r['episode_id'] in seen:continue
  seen.add(r['episode_id']);selected.append(r)
 return selected,ledger

def evaluate(row,f,point,bad=None):
 h=f['H1'];m=f['M1'];m15=f['M15'];k=int(row['signal_idx']);A=float(row['A'] if 'A' in row else h.iloc[k].A);s=row.get('sign',1);when=pd.Timestamp(row['signal_time']);mi=int(m15.t.searchsorted(when));out=[]
 common={**row,'A':A,'direction':'BUY' if s==1 else 'SELL','management':'BE_H1_2C'}
 if mi>=len(m15) or not np.isfinite(A) or A<=0:return [{**common,'target_A':tp,'status':'CENSORED','reason':'no_entry_or_ATR','net_R':np.nan,'score_R_min':np.nan,'entry_time':'','month':'','horizon_complete':False} for tp in [2,3]]
 e=m15.iloc[mi];E=float(e.open);et=e.t;j=int(h.t.searchsorted(et));last=j+23;complete=last<len(h);hs=h.iloc[j:min(last+1,len(h))];end=hs.end.iloc[-1] if len(hs) else et
 d=m.iloc[int(m.t.searchsorted(et)):int(m.t.searchsorted(end))];terminal=float(hs.close.iloc[-1]) if len(hs) else E
 mismatch=bool(bad and (any(t in bad['H1'] for t in hs.t) or et in bad['M15']))
 common.update(entry_time=str(et),entry=E,month=str(et)[:7],horizon_end=str(end),horizon_complete=complete,SL=E-s*3*A,TP2=E+s*2*A,TP3=E+s*3*A,source_mismatch=mismatch,first_quote_time=str(d.t.iloc[0]) if len(d) else '',MFE_A=float((s*((d.high if s==1 else d.low)-E)).max()/A) if len(d) else np.nan,MAE_A=float((-s*((d.low if s==1 else d.high)-E)).max()/A) if len(d) else np.nan)
 count=0;times=[]
 for r in hs.itertuples(index=False):
  count=count+1 if s*(r.close-E)>=A else 0
  if count>=2:times.append(str(r.end))
 for tp in [2,3]:
  result=be.scheduled(d,E,A,s,tp,times,terminal,end);paths=result.pop('paths');xt=pd.Timestamp(result['exit_time_last']);ci=int(d.t.searchsorted(xt,side='right'))-1;cr=d.iloc[ci] if ci>=0 else e;cost=point*(float(e.spread)+float(cr.spread))/(6*A)
  valid=complete and len(d)>0 and not mismatch;rowout={**common,**result,'target_A':tp,'provisional_status':result['status'],'status':result['status'] if valid else 'CENSORED','reason':'source_mismatch' if mismatch else '' if complete else 'incomplete_horizon','spread_cost_R':cost,'net_R':result['gap_adjusted_R_min']-cost if valid else np.nan,'BE_qualification_times':';'.join(times),'paths_json':json.dumps(paths)}
  if not valid:
   for col in ['score_R_min','score_R_max','gap_adjusted_R_min','gap_adjusted_R_max']:rowout[col]=np.nan
  out.append(rowout)
 return out

def perf(rows):
 q=pd.DataFrame(rows);n=len(q)
 if n and 'entry_time' in q:q=q.sort_values('entry_time',kind='stable')
 counts=q.status.value_counts() if n else {};x=q.net_R.dropna() if n else pd.Series(dtype=float);scored=len(x)
 return {'entries':n,'scored':scored,**{s:int(counts.get(s,0)) for s in ['WIN','LOSS','BE','TIMEOUT','AMBIGUOUS','CENSORED']},'gross_R':float(q.score_R_min.sum()) if n and 'score_R_min' in q else 0.,'net_R':float(x.sum()),'mean_net_R':float(x.mean()) if scored else None,'months':int(q.loc[q.net_R.notna(),'month'].nunique()) if scored else 0,'selection_score':float(x.sum()-.25*x.std(ddof=1)*np.sqrt(scored)) if scored>1 else -999.,'max_drawdown_R':float((pd.concat([pd.Series([0.]),x.reset_index(drop=True)]).cumsum().cummax()-pd.concat([pd.Series([0.]),x.reset_index(drop=True)]).cumsum()).max()) if scored else 0.}

def partition(rows,start,stop):return [r for r in rows if r.get('entry_time','')>=start and r.get('entry_time','')<stop and r.get('horizon_end','9999')<=stop and r.get('horizon_complete',False)]
