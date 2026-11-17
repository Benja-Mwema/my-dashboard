"""AURUM four-index candidates. Native closed bars; no trading API operations."""
from pathlib import Path
import sys,json,hashlib,datetime,argparse,shutil,time,traceback
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import four_indices_engine as engine

ROOT=Path(__file__).resolve().parent
ARCHIVE=Path(r'C:\Ben\mt5\research_four_indices_ws30_20261117_v01')
CONTRACT=json.loads((ROOT/'candidates.json').read_text())
TF_MIN={'M1':1,'M15':15,'H1':60,'H4':240,'D1':1440,'W1':10080}

def clean(o):
 if isinstance(o,dict):return {k:clean(v) for k,v in o.items()}
 if isinstance(o,(tuple,list)):return [clean(v) for v in o]
 if isinstance(o,(pd.Timestamp,datetime.datetime)):return str(o)
 if isinstance(o,(np.bool_,)):return bool(o)
 if isinstance(o,(np.integer,)):return int(o)
 if isinstance(o,(float,np.floating)):return float(o) if np.isfinite(o) else None
 return o
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
 tmp.write_text(json.dumps(clean(obj),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8');tmp.replace(p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def epoch(t):return int(pd.Timestamp(t).timestamp())
def label(t):return pd.to_datetime(t,unit='s').strftime('%Y-%m-%d %H:%M:%S')
def candidates(frames,c):
 selected,ledger=engine.detect(frames,c['variant'])
 return [s for s in selected if not c['branch'] or s['branch']==c['branch']],ledger

def source(stem,c,offline):
 folder=ROOT/'cache'/c['symbol'];folder.mkdir(parents=True,exist_ok=True)
 quote=None;versions=0
 if not offline:
  import MetaTrader5 as mt
  assert mt.initialize(),mt.last_error()
  assert mt.terminal_info().connected,'MT5 disconnected'
  assert mt.symbol_select(c['symbol'],True)
  info=mt.symbol_info(c['symbol']);tick=mt.symbol_info_tick(c['symbol'])
  assert info and info.point==.1 and info.digits==1 and tick and tick.time>0,'Symbol metadata/quote mismatch'
  quote=int(tick.time)
 try:
  for tf in TF_MIN:
   archived=pd.read_csv(ARCHIVE/'data'/c['symbol']/(tf+'.csv'))
   archived=archived[archived.confirmed_by_later_bar.eq(1)].reset_index(drop=True)
   path=folder/(tf+'.csv');raw=archived if offline or not path.exists() else pd.read_csv(path)
   if not offline:
    count={'M1':10000,'M15':3000,'H1':1200,'H4':500,'D1':150,'W1':60}[tf]
    rr=mt.copy_rates_from_pos(c['symbol'],getattr(mt,'TIMEFRAME_'+tf),0,count)
    assert rr is not None and len(rr)>5,'Missing native '+tf
    tail=pd.DataFrame(rr).sort_values('time').iloc[:-1].copy()
    tail=tail[tail.time+TF_MIN[tf]*60<=quote]
    common=raw.merge(tail,on='time',suffixes=('_old','_new'))
    assert len(common)>=min(3,len(raw)),'Native/cache overlap missing: '+tf
    for k in ['open','high','low','close']:
     assert np.allclose(common[k+'_old'],common[k+'_new'],atol=1e-7,rtol=0),'Native OHLC revision: '+tf+' '+k
    versions+=int(common.tick_volume_old.ne(common.tick_volume_new).sum())
    tail['broker_time']=pd.to_datetime(tail.time,unit='s').dt.strftime('%Y-%m-%d %H:%M:%S');tail['confirmed_by_later_bar']=1
    raw=pd.concat([raw,tail[tail.time>raw.time.max()]],ignore_index=True)
   assert len(raw)>=len(archived) and np.array_equal(raw.time.iloc[:len(archived)],archived.time),'Archived prefix changed: '+tf
   for k in ['open','high','low','close']:
    assert np.allclose(raw[k].iloc[:len(archived)],archived[k],atol=1e-7,rtol=0),'Archived OHLC changed'
   assert raw.time.is_unique and raw.time.is_monotonic_increasing and np.isfinite(raw[['open','high','low','close']]).all().all()
   assert ((raw.low>0)&(raw.low<=raw[['open','close']].min(axis=1))&(raw.high>=raw[['open','close']].max(axis=1))).all(),'Invalid OHLC'
   temp=path.with_suffix('.csv.tmp');raw.to_csv(temp,index=False);temp.replace(path)
 finally:
  if not offline:mt.shutdown()
 f=engine.load_frames(folder)
 # Price integrity is required. Volume-only provider revisions are counted but
 # do not change these price-only rules or rewrite archived inputs.
 for tf,freq in [('H1','h'),('M15','15min')]:
  a=f['M1'].groupby(f['M1'].t.dt.floor(freq)).agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'))
  q=f[tf].set_index('t').join(a,rsuffix='_m1')
  assert q.open_m1.notna().all(),'M1 coverage missing for '+tf
  for k in ['open','high','low','close']:assert np.allclose(q[k],q[k+'_m1'],atol=1e-7,rtol=0),'M1 aggregation mismatch '+tf+' '+k
 return f,quote,versions

def predicates(s,f,c,ledger):
 h=f['H1'];k=int(s['signal_idx']);b=h.iloc[k];when=str(b.end);rows=[]
 def add(name,value,condition,passed=None,at=None):rows.append(dict(label=name,value=clean(value),condition=condition,passed=passed,available_at=at or when))
 add('Candidate branch',s['branch'],c['priority_contract'],None)
 add('Signal close',b.close,'Completed native H1 candle; forming bars excluded',True)
 if c['variant']['family']=='D04':
  fail=h.iloc[int(s['failure_idx'])];B=s['B'];Z=s['zone_level']
  add('Seed floor B',B,'Lowest low on seed date through initial breakout',None,str(s['seed_time']))
  add('Failure close',fail.close,'Close < B',bool(fail.close<B),str(fail.end))
  if s['branch']=='EARLIER':
   add('Retest zone Z',Z,'B − '+str(c['variant']['changes'].get('zone',.5))+' × failure ATR',None,str(fail.end))
   add('Prior close',h.close.iloc[k-1],'Prior close < Z',bool(h.close.iloc[k-1]<Z))
   add('Retest high',b.high,'High ≥ Z',bool(b.high>=Z))
   add('Retest close',b.close,'Close < Z',bool(b.close<Z))
  else:add('Acceptance high',b.high,'Entire next H1 range below B',bool(b.high<B))
 elif c['variant']['family']=='Combined':
  seed=h.iloc[int(h.end.searchsorted(pd.Timestamp(s['seed_time'])))];R=s['R'];ref=f['D1'][f['D1'].t.eq(seed.ref_day)].iloc[0]
  w=f['W1'][f['W1'].end<=seed.ref_day].tail(4)
  add('Prior daily high R',R,'Completed D1 reference',None,str(seed.ref_known))
  add('Seed close',seed.close,'Close > R',bool(seed.close>R),str(seed.end))
  add('Acceptance low',b.low,'Next H1 low > R',bool(b.low>R))
  add('Reference D1 close',ref.close,'Above highs of preceding four completed W1 bars',bool(len(w)==4 and ref.close>w.high.max()),str(ref.end))
  add('Four-week high',w.high.max(),'Weeks end no later than reference D1 open',None,str(seed.ref_known))
 else:
  e=next((r for r in ledger if r.get('episode_id')==s['episode_id']),{})
  add('Prior daily reference',s['reference'],'Daily low for BUY / high for SELL')
  add('Pre-breach ATR',s['A'],'Fixed entry-risk scale before breach')
  add('Breach depth / ATR',e.get('depth_A'),'At least 1 ATR',bool(e.get('depth_A',0)>=1))
  add('Defended level',s['defense'],'Reclaim → bounded defense → resumption; original reservations retained')
  add('Post-defense close guard',True,'No close through defended extreme before confirmation',True)
 return rows

def build(stem,offline=False,prefix_checks=False):
 c=CONTRACT['candidates'][stem]
 for name,want in CONTRACT['engine_hashes'].items():assert sha(ROOT/name)==want,'Frozen detector changed: '+name
 f,quote,volume_revisions=source(stem,c,offline);signals,ledger=candidates(f,c)
 ref=pd.read_csv(ARCHIVE/'results/all_baseline_selected_outcomes.csv')
 ref=ref[ref.series.eq('SELECTED')&ref.symbol.eq(c['symbol'])&ref.configuration.eq(c['variant']['id'])]
 if c['branch']:ref=ref[ref.branch.eq(c['branch'])]
 ref_signals=ref[ref.target_A.eq(2)].sort_values('signal_time');assert len(ref_signals)==c['archived_entries']
 frozen_h=pd.read_csv(ARCHIVE/'data'/c['symbol']/'H1.csv');frozen_h=frozen_h[frozen_h.confirmed_by_later_bar.eq(1)]
 cutoff=pd.Timestamp(frozen_h.broker_time.iloc[-1])+pd.Timedelta(hours=1)
 historical=[s for s in signals if pd.Timestamp(s['signal_time'])<=cutoff]
 assert len(historical)==len(ref_signals),'Archived candidate admission changed'
 assert [(s['signal_time'],int(s['sign'])) for s in historical]==[(str(r.signal_time),int(r.sign)) for r in ref_signals.itertuples()],'Archived signal identity changed'
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();entries=[];checked=0;seen_path=ROOT/(stem+'_first_seen.json');seen=json.loads(seen_path.read_text()) if seen_path.exists() else {}
 for s in signals:
  profiles=engine.evaluate(s,f,.1);k=int(s['signal_idx']);A=float(s.get('A',f['H1'].A.iloc[k]));sgn=int(s['sign']);sid=stem.upper()+'_'+str(epoch(s['signal_time']))+'_'+('BUY' if sgn==1 else 'SELL')
  older=pd.Timestamp(s['signal_time'])<=cutoff;outs={}
  for p in profiles:
   if older:
    row=ref[ref.signal_time.eq(p['signal_time'])&ref.target_A.eq(p['target_A'])].iloc[0]
    assert p['status']==row.status,'Archived outcome status changed'
    for field in ['entry','A','SL','TP2','TP3','net_R','score_R_min','gap_adjusted_R_min']:
     if pd.notna(row[field]):assert abs(p[field]-row[field])<1e-8,'Archived outcome value changed: '+field
    assert p['entry_time']==row.entry_time and p['exit_time_first']==row.exit_time_first,'Archived event timing changed'
    checked+=1
   paths=json.loads(p.get('paths_json','[]'));final=p['status'] not in ['CENSORED','AMBIGUOUS'] and p.get('net_R') is not None
   outs[str(p['target_A'])]=dict(status=p['status'],provisional_status=p.get('provisional_status'),final=final,net_R=p.get('net_R'),gross_R=p.get('score_R_min'),gap_adjusted_R=p.get('gap_adjusted_R_min'),spread_cost_R=p.get('spread_cost_R'),exit_time=p.get('exit_time_first') if final else None,exit_price=paths[0]['price_proxy'] if final and len(paths)==1 else None,BE_armed_at=p.get('first_activation_time') or None,horizon_end=p.get('horizon_end'),MFE_A=p.get('MFE_A'),MAE_A=p.get('MAE_A'),opening_gap=p.get('opening_gap_any'),paths=paths,reason=p.get('reason'))
  p=profiles[0];seen.setdefault(sid,now)
  entries.append(dict(id=sid,direction='BUY' if sgn==1 else 'SELL',sign=sgn,rule=c['rule_label'],family=c['variant']['family'],branch=s['branch'],signal_bar_open=str(f['H1'].t.iloc[k]),signal_available_at=str(s['signal_time']),entry_time=p.get('entry_time') or None,entry_price=p.get('entry'),ATR=A,SL=p.get('SL'),TP2=p.get('TP2'),TP3=p.get('TP3'),outcomes=outs,anchors={n:clean(s.get(n)) for n in ['reference','defense','R','B','Q','P','zone_level','failure_ATR','seed_time']},predicates=predicates(s,f,c,ledger),cohort='archived' if older else 'post_research',origin='Archived research reconstruction' if older else 'Post-research observation; first seen '+seen[sid],first_seen_utc=seen[sid],model_hash=CONTRACT['model_hash']))
 assert checked==2*c['archived_entries']
 h=f['H1'].copy()
 for period in [10,20,50]:h['ema'+str(period)]=h.close.ewm(span=period,adjust=False).mean()
 candles=[dict(time=int(r.time),open_time=str(r.t),close_time=str(r.end),open=r.open,high=r.high,low=r.low,close=r.close,ema10=r.ema10,ema20=r.ema20,ema50=r.ema50,model_atr14=r.A) for r in h.itertuples()]
 validation=dict(archived_signals_exact=c['archived_entries'],archived_outcomes_exact=checked,price_aggregation_verified=True,source_volume_revisions=volume_revisions)
 if prefix_checks:
  checks=[]
  for cut in ['2026-04-01','2026-07-01','2026-10-01']:
   prefix={tf:x[x.end<=cut].copy().reset_index(drop=True) for tf,x in f.items()}
   got,_=candidates(prefix,c);want=[s for s in signals if s['signal_time']<=cut+' 00:00:00']
   assert [(s['signal_time'],s['sign']) for s in got]==[(s['signal_time'],s['sign']) for s in want],(stem,cut,'Causal prefix mismatch')
   checks.append(cut)
  validation['causal_prefix_checks']=checks
 out=dict(version=c['version'],symbol=c['symbol'],point=.1,digits=1,generated_at=now,latest_completed_h1=str(h.end.iloc[-1]),quote_broker_time=label(quote) if quote else None,candles=candles,entries=entries,validation=validation,health=dict(state='REPLAY' if offline else 'SOURCE_LAG' if quote-epoch(h.end.iloc[-1])>3600 else 'OK',refreshed_at=now,last_confirmed_broker_H1=str(h.end.iloc[-1])),meta=dict(timeframe='H1',paper_only=True,broker_orders_enabled=False,validation_status='RESEARCH_CANDIDATE_INDEPENDENT_VALIDATION_PENDING',research_cutoff=str(cutoff),model_hash=CONTRACT['model_hash'],candidate=c,management=CONTRACT['management'],clock='Native broker labels; historical EAT conversion unverified'),current=dict(ema_order='BULLISH' if h.ema10.iloc[-1]>h.ema20.iloc[-1]>h.ema50.iloc[-1] else 'BEARISH' if h.ema10.iloc[-1]<h.ema20.iloc[-1]<h.ema50.iloc[-1] else 'MIXED'))
 atomic(ROOT/'site'/(stem+'-data.json'),out)
 if offline:atomic(ROOT/'site'/(stem+'-replay.json'),out)
 else:atomic(seen_path,seen)
 atomic(ROOT/'site'/(stem+'-acceptance.json'),validation)
 atomic(ROOT/'site'/(stem+'-rules.json'),dict(candidate=c,management=CONTRACT['management'],model_hash=CONTRACT['model_hash'],engine_hashes=CONTRACT['engine_hashes']))
 (ROOT/(stem+'_build_error.json')).unlink(missing_ok=True)
 print(json.dumps(dict(symbol=c['symbol'],entries=len(entries),asof=out['latest_completed_h1'],health=out['health']['state'],validation=validation)),flush=True)
 return out

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--prefix-checks',action='store_true');parser.add_argument('--symbol',choices=list(CONTRACT['candidates']));args=parser.parse_args()
 failures=[]
 for stem in [args.symbol] if args.symbol else CONTRACT['candidates']:
  try:build(stem,args.offline,args.prefix_checks)
  except Exception as e:
   atomic(ROOT/(stem+'_build_error.json'),dict(error=str(e),at=datetime.datetime.now(datetime.timezone.utc).isoformat()));traceback.print_exc();failures.append(stem)
 if failures:sys.exit(1)
