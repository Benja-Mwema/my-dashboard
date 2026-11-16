"""DAX40 frozen research snapshot. Native MT5 read-only data; no order APIs."""
from pathlib import Path
import json,hashlib,sys,datetime,argparse,os
import pandas as pd,numpy as np
from classifier import classify
ROOT=Path(__file__).resolve().parent;WORK=ROOT/'engine_root';CACHE=ROOT/'cache';SITE=ROOT/'site'
RULES={'RCV':'RCV-E50','BRT':'BRT-H4-C2','DBR':'DBR','VCBS':'VCBS','ETP3':'ETP3','BFC075':'BFC075'}
FORMULAS={'RCV':'RCV-E50','BRT':'P01+P07+P10','DBR':'P08+P10+P27','VCBS':'P03+P12+P29','ETP3':'P15+P16+P29','BFC075':'P07+P19+P28'}
def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,np.generic):return clean(x.item())
 if isinstance(x,float) and not np.isfinite(x):return None
 return x
def write(path,data):
 b=json.dumps(clean(data),ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n';tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(b,encoding='utf-8');tmp.replace(path)
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load_source(offline):
 CACHE.mkdir(exist_ok=True);config=json.loads((ROOT/'config.json').read_text());frames={};checks=[]
 if not offline:
  import MetaTrader5 as mt
  assert mt.initialize(),mt.last_error()
  assert mt.symbol_select('DAX40.pro',True)
  info=mt.symbol_info('DAX40.pro');assert abs(info.point-.1)<1e-12,'Frozen spread-point convention differs'
 try:
  for name,secs in [('H1',3600),('H4',14400),('D1',86400),('M1',60)]:
   p=CACHE/(name+'.csv');base=p if p.exists() else Path(config['research_source'])/(name+'.csv');d=pd.read_csv(base)
   if not offline:
    tick=mt.symbol_info_tick('DAX40.pro');assert tick is not None;now=datetime.datetime.fromtimestamp(tick.time+secs,datetime.timezone.utc);start=datetime.datetime.fromtimestamp(int(d.time.max())-7*86400,datetime.timezone.utc)
    rr=mt.copy_rates_range('DAX40.pro',getattr(mt,'TIMEFRAME_'+name),start,now);assert rr is not None and len(rr),(name,mt.last_error())
    new=pd.DataFrame(rr);latest_bar=mt.copy_rates_from_pos('DAX40.pro',getattr(mt,'TIMEFRAME_'+name),0,1);assert latest_bar is not None and len(latest_bar);forming_open=int(latest_bar[-1]['time']);new=new[new.time<forming_open]
    common=d.merge(new,on='time',suffixes=('_old','_new'))
    for col in ['open','high','low','close','tick_volume']:
     assert np.allclose(common[col+'_old'],common[col+'_new'],atol=1e-7,rtol=0),f'{name} historical revision {col}'
    assert len(common)>0,f'{name} source overlap absent'
    checks.append(dict(tf=name,overlap=len(common),new_bars=int((new.time>d.time.max()).sum()),forming_open=forming_open,native_tick_time=int(tick.time)))
    d=pd.concat([d,new]).drop_duplicates('time',keep='first').sort_values('time').reset_index(drop=True)
   assert not d.time.duplicated().any() and d.time.is_monotonic_increasing
   assert (d.high>=d[['open','low','close']].max(axis=1)).all() and (d.low<=d[['open','high','close']].min(axis=1)).all()
   frames[name]=d
  # Do not partially advance cache if any timeframe fails source validation.
  for name,d in frames.items():
   p=CACHE/(name+'.csv')
   if not p.exists() or len(d)!=sum(1 for _ in p.open())-1:d.to_csv(p,index=False)
 finally:
  if not offline:mt.shutdown()
 return frames,checks

def markets(d1):
 d=pd.read_csv(ROOT/'frozen/market_d1.csv');common=d.merge(d1,on='time',suffixes=('_a','_b'))
 for col in ['open','high','low','close']:assert np.allclose(common[col+'_a'],common[col+'_b'],rtol=0,atol=1e-7)
 d=pd.concat([d,d1]).drop_duplicates('time',keep='first').sort_values('time');d['date']=pd.to_datetime(d.time,unit='s',utc=True).dt.strftime('%Y-%m-%d');d=d[pd.to_datetime(d.date).dt.dayofweek<5].copy();d['available']=d.time+86400;d,sh=classify(d)
 ref=pd.read_csv(ROOT/'frozen/daily_states.csv');over=d.merge(ref,on='time',suffixes=('_a','_b'));assert len(over)==len(ref)
 for col in ['trend','vol']:assert (over[col+'_a']==over[col+'_b']).all()
 for col in ['ema20','ema50','atr14','vol_ratio']:assert np.allclose(over[col+'_a'],over[col+'_b'],equal_nan=True)
 episodes=[];starts=np.flatnonzero(d.trend.ne(d.trend.shift()).to_numpy())
 for i,a in enumerate(starts):
  b=starts[i+1] if i+1<len(starts) else len(d);g=d.iloc[a:b]
  if g.date.iloc[-1]<'2016-01-01':continue
  episodes.append(dict(state=g.trend.iloc[0],start=g.date.iloc[0],available=int(g.available.iloc[0]),inherited=g.date.iloc[0]<'2016-01-01'))
 catalog=pd.read_csv(ROOT/'frozen/catalogue.csv');lookup=dict(zip(catalog.sequence,catalog.ID));timeline=[]
 for i in range(2,len(episodes)):
  trio=episodes[i-2:i+1]
  if any(x['inherited'] or x['state']=='UNKNOWN' for x in trio):continue
  seq=' → '.join(x['state'] for x in trio);last=trio[-1];timeline.append(dict(formation=lookup.get(seq,'OTHER'),sequence=seq,available=last['available'],candle_date=last['start'],trend=last['state']))
 refm=pd.read_csv(ROOT/'frozen/formations.csv');old=[x for x in timeline if x['candle_date']<=refm.recognized_date.max()];assert len(old)==len(refm)
 for x,(_,r) in zip(old,refm.iterrows()):assert x['sequence']==r.sequence and x['available']==int(pd.Timestamp(r.recognized_EAT).timestamp())
 return d,timeline,lookup

def prepare(frames,q):
 h,m,h4,d1=[frames[k].copy() for k in ['H1','M1','H4','D1']]
 z=m.assign(hour=m.time//3600*3600).groupby('hour').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),tick_volume=('tick_volume','sum'))
 v=h.merge(z,left_on='time',right_index=True,how='left',suffixes=('','_m1'));ok=np.ones(len(h),dtype=bool)
 for col in ['open','high','low','close','tick_volume']:ok &= np.isclose(v[col],v[col+'_m1'],atol=1e-6,rtol=0)
 h['coverage_ok']=ok;h['complete_at_extraction']=True
 for x in [h,h4]:
  for n in [20,50]:x[f'ema{n}']=x.close.ewm(span=n,adjust=False).mean()
 h['floor24']=h.low.shift().rolling(24).min();h['high24']=h.high.shift().rolling(24).max();h['ema50_delta3']=h.ema50-h.ema50.shift(3)
 tr=np.maximum(h.high-h.low,np.maximum((h.high-h.close.shift()).abs(),(h.low-h.close.shift()).abs()));tr.iloc[0]=h.high.iloc[0]-h.low.iloc[0];h['tr']=tr;a=np.full(len(h),np.nan);a[13]=tr.iloc[:14].mean()
 for i in range(14,len(h)):a[i]=(13*a[i-1]+tr.iloc[i])/14
 h['atr14']=a
 p=WORK/'dax40_research_v0_1/source';p.mkdir(parents=True,exist_ok=True);d1.to_csv(p/'D1.csv',index=False);d1=q.prep(h,h4)
 return h,m,h4,d1

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--offline',action='store_true');ap.add_argument('--force',action='store_true');args=ap.parse_args();SITE.mkdir(exist_ok=True)
 hashes=json.loads((ROOT/'frozen/ENGINE_SOURCE_HASHES.json').read_text())
 for f,v in hashes.items():assert hashlib.sha256((WORK/f).read_bytes()).hexdigest()==v
 config=json.loads((ROOT/'config.json').read_text());assert config['broker_orders_enabled'] is False and config['paper_only'] is True
 frames,source_checks=load_source(args.offline);latest={k:int(v.time.iloc[-1]) for k,v in frames.items()};d,timeline,lookup=markets(frames['D1']);output=SITE/'dax40-data.json'
 if output.exists() and not args.force:
  previous=json.loads(output.read_text(encoding='utf-8'))
  if previous['meta']['source_last']==latest:
   previous['market']['trend_age_bars']=int(len(d)-1-np.flatnonzero(d.trend.ne(d.trend.shift()).to_numpy())[-1]);previous['market']['volatility_age_bars']=int(len(d)-1-np.flatnonzero(d.vol.ne(d.vol.shift()).to_numpy())[-1]);previous['health']['refreshed_at']=stamp();previous['health']['source_checks']=source_checks;previous['health']['market_data_age_hours']=(max([x.get('native_tick_time',0) for x in source_checks] or [latest['H1']+3600])-latest['H1']-3600)/3600;previous['health']['state']='STALE' if previous['health']['market_data_age_hours']>3 else 'OK';write(output,previous);print('UNCHANGED_BARS_SOURCE_REVERIFIED');return
 sys.path.insert(0,str(WORK/'dax40_four_more/code'));import search as q;import structures as st
 e=q.e;h,m,h4,d1=prepare(frames,q);print('SOURCE_AND_MARKET_PARITY_PASS',len(d),flush=True)
 start=e.prior.epoch('2016-01-01');end=int(h.time.max())+3601
 a=e.detect(h,start,end);b=e.prior.detect(h,start=start,end=end);cc=st.inventory(h,start,end)
 matches=[x for x in a.matches if x['family'] in ['BRT','DBR']]+[dict(x,family='RCV',direction=1) for x in b.matches]+[x for x in cc[2] if x['family'] in ['VCBS','ETP3','BFC075']]
 ff={x['seed_id']:q.context(h,h4,d1,x) for x in matches};ms=e.mirrored(m);rows=[]
 for family,formula in FORMULAS.items():
  eligible=[]
  for x in matches:
   if x['family']!=family:continue
   f=ff[x['seed_id']];passed=(f['efficiency12']>=.5 and f['body_fraction']>=2/3) if family=='RCV' else q.passed(f,q.combof(formula))
   assert f['h4_available']<=x['confirmation_available'] and f['d1_available']<=x['confirmation_available']
   if passed:eligible.append(x)
  admitted=[x for x in e.prior.admit(eligible) if x['admission']=='ADMITTED'];assert all(y['confirm_i']-x['confirm_i']>=24 for x,y in zip(admitted,admitted[1:]))
  for x in admitted:rows.append(dict(e.score(x,h,m,ms),formula=formula))
  print('SCORED',family,len(admitted),flush=True)
 trades=pd.DataFrame(rows).sort_values('confirmation_available');trades=pd.merge_asof(trades,d[['available','date','trend','vol','trend_raw','vol_raw']].rename(columns={'available':'state_available','date':'state_date'}),left_on='confirmation_available',right_on='state_available',direction='backward');trades=pd.merge_asof(trades,pd.DataFrame(timeline).rename(columns={'available':'formation_available','trend':'formation_trend'}),left_on='confirmation_available',right_on='formation_available',direction='backward');trades['formation']=trades.formation.fillna('UNCLASSIFIED');assert (trades.state_available<=trades.confirmation_available).all()
 ref=pd.read_csv(ROOT/'frozen/trades.csv');ids=list(zip(ref.family,ref.seed_id));recent=trades[trades.confirmation_available<=ref.confirmation_available.max()];assert set(zip(recent.family,recent.seed_id))==set(ids)
 joined=ref.merge(trades,on=['family','seed_id'],suffixes=('_ref','_now'));assert len(joined)==len(ref)
 closed=joined[joined.status_ref!='CENSORED']
 assert (closed.status_ref==closed.status_now).all()
 for col in ['confirm_time','confirmation_available','entry_time','entry','stop','target','exit_time','net_r_low','net_r_high']:
  assert np.allclose(closed[col+'_ref'],closed[col+'_now'],atol=1e-7,rtol=0,equal_nan=True),col
 assert (joined.ID==joined.formation).all() and (joined.trend_ref==joined.trend_now).all() and (joined.vol_ref==joined.vol_now).all()
 signals=[]
 for row in trades.to_dict('records'):
  f=ff[row['seed_id']];fam=row['family'];clauses=[('efficiency12','>=',.5),('body_fraction','>=',2/3)] if fam=='RCV' else [q.CLAUSES[i] for i in q.combof(FORMULAS[fam])]
  predicates=[dict(feature=k,operator=op,threshold=v,value=f[k],passed=bool(f[k]>v if op=='>' else f[k]>=v if op=='>=' else f[k]<=v)) for k,op,v in clauses];assert all(z['passed'] for z in predicates)
  row.update(id=fam+':'+row['seed_id'],rule=RULES[fam],side='BUY' if row['direction']==1 else 'SELL',features=f,predicates=predicates,display_status=row['status'],origin='HISTORICAL_REPLAY' if (fam,row['seed_id']) in ids else 'POST_FREEZE_RECONSTRUCTION_NOT_PROSPECTIVE')
  if row['status']=='CENSORED' and row['coverage_reason']=='INSUFFICIENT_24_H1_TAIL':
   future=m[m.time>=row['confirmation_available']];row['display_status']='WAITING_ENTRY'
   if len(future):
    minute=future.iloc[0];risk=2*row['atr'];row.update(display_status='OPEN_PENDING_OUTCOME',entry_time=int(minute.time),entry=float(minute.open),stop=float(minute.open-row['direction']*risk),target=float(minute.open+row['direction']*risk))
  if np.isfinite(row.get('r_low',np.nan)) and np.isfinite(row.get('entry',np.nan)):row['exit_price']=row['entry']+row['direction']*2*row['atr']*row['r_low']
  signals.append(row)
 assert len(signals)==len({x['id'] for x in signals})
 last=d.iloc[-1];age=(max([x.get('native_tick_time',0) for x in source_checks] or [latest['H1']+3600])-latest['H1']-3600)/3600
 market=dict(trend_age_bars=int(len(d)-1-np.flatnonzero(d.trend.ne(d.trend.shift()).to_numpy())[-1]),volatility_age_bars=int(len(d)-1-np.flatnonzero(d.vol.ne(d.vol.shift()).to_numpy())[-1]),trend=last.trend,volatility=last.vol,raw_trend=last.trend_raw,raw_volatility=last.vol_raw,state_available=int(last.available),candle_date=last.date,formation=timeline[-1],ema20=float(last.ema20),ema50=float(last.ema50),atr14=float(last.atr14),vol_ratio=float(last.vol_ratio))
 snapshot=dict(version=config['version'],symbol='DAX40.pro',point=.1,digits=1,meta=dict(generated_at=stamp(),source_last=latest,broker_orders_enabled=False,paper_only=True,rule_hashes=hashes,market_gating=False,forecast_model=None),health=dict(state='STALE' if age>3 else 'OK',refreshed_at=stamp(),market_data_age_hours=age,source_checks=source_checks,parity_h1_pass=int(h.coverage_ok.sum()),parity_h1_total=len(h)),market=market,formations=timeline,rules=[dict(family=k,name=v,formula=FORMULAS[k]) for k,v in RULES.items()],signals=signals,candles=clean(h[['time','open','high','low','close','ema20','ema50']].round(6).values.tolist()),validation=dict(archived_signals_exact=len(ref),archived_closed_outcomes_exact=len(closed),market_rows_exact=len(pd.read_csv(ROOT/'frozen/daily_states.csv')),availability_and_hashes=True))
 write(output,snapshot);write(ROOT/'acceptance.json',dict(status='PASS',at=stamp(),**snapshot['validation'],signals=len(signals),source_last=latest));trades.to_csv(CACHE/'latest_trades.csv',index=False);print('SNAPSHOT_PASS',len(signals),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as exc:
  write(ROOT/'build_error.json',dict(status='FAILED_PREVIOUS_SNAPSHOT_RETAINED',at=stamp(),reason=str(exc)));raise
