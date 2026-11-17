from pathlib import Path
import json,hashlib,datetime,argparse,sys,traceback
import pandas as pd,numpy as np
from engine import scan
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def label(t):return pd.to_datetime(t,unit='s').strftime('%Y-%m-%d %H:%M:%S')
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,separators=(',',':'),allow_nan=False),encoding='utf-8');tmp.replace(p)
def clean(obj):
 if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
 if isinstance(obj,(list,tuple)):return [clean(v) for v in obj]
 if isinstance(obj,(pd.Timestamp,datetime.datetime)):return obj.strftime('%Y-%m-%d %H:%M:%S')
 if isinstance(obj,(np.integer,)):return int(obj)
 if isinstance(obj,(np.bool_,)):return bool(obj)
 if isinstance(obj,(float,np.floating)):return float(obj) if np.isfinite(obj) else None
 return obj
def project(raw,now,quote=None,entry_hint=None):
 f,signals,audit=scan(raw);entries=[]
 for _,s in signals.iterrows():
  if s.decision.year<2026:continue
  i=int(s.i);rec=clean(s.to_dict());rec.update(id=f"GBPUSD_E1_M30_{int(s.time)}_{s.side}",direction=s.side,signal_bar_open=str(s.date),signal_available_at=str(s.decision),entry_time=None,entry_price=None,entry_status='PENDING_ENTRY',origin='Historical reconstruction',outcomes={})
  if i+1<len(f):
   if f.time.iloc[i+1]-s.time!=1800:rec['entry_status']='CANCELLED_GAP'
   else:rec.update(entry_status='ENTERED',entry_time=str(f.date.iloc[i+1]),entry_price=float(f.open.iloc[i+1]))
  elif entry_hint is not None:
   if entry_hint['time']-s.time==1800:rec.update(entry_status='ENTERED',entry_time=label(entry_hint['time']),entry_price=float(entry_hint['open']))
   elif entry_hint['time']>s.time+1800:rec['entry_status']='CANCELLED_GAP'
  for h in (12,24):
   o=dict(status=rec['entry_status'] if rec['entry_status']!='ENTERED' else 'PENDING_OUTCOME',gross_pips=None,mfe_pips=None,mae_pips=None,adverse35=None,end_time=None,end_price=None,forward_gap=None)
   if rec['entry_status']=='ENTERED':
    w=f.iloc[i+1:min(i+h+1,len(f))];E=rec['entry_price'];d=1 if s.side=='BUY' else -1
    if len(w):
     mfe=max(0,w.high.max()-E) if d==1 else max(0,E-w.low.min());mae=max(0,E-w.low.min()) if d==1 else max(0,w.high.max()-E)
     o.update(observed_bars=len(w),partial_mfe_pips=round(mfe/.0001,8),partial_mae_pips=round(mae/.0001,8),mark_pips=round(d*(w.close.iloc[-1]-E)/.0001,8),forward_gap=bool(w.time.diff().dropna().ne(1800).any()))
    if len(w)==h:
     gross=d*(int(round(w.close.iloc[-1]/.00001))-int(round(E/.00001)))/10;maep=round(mae/.0001,8)
     o.update(status='COMPLETE',gross_pips=gross,net2_pips=round(gross-2,8),mfe_pips=round(mfe/.0001,8),mae_pips=maep,adverse35=maep<=35,end_time=str(w.date.iloc[-1]+pd.Timedelta(minutes=30)),end_price=float(w.close.iloc[-1]),mfe_atr=mfe/s.atr,mae_atr=mae/s.atr)
   if o['status']=='COMPLETE':
    fav=E+d*2*s.atr;adv=E-d*s.atr;hit='unresolved'
    for z in w.itertuples(index=False):
     hf=z.high>=fav if d==1 else z.low<=fav;ha=z.low<=adv if d==1 else z.high>=adv
     if hf or ha:hit='ambiguous' if hf and ha else 'favorable_first' if hf else 'adverse_first';break
    o['first_hit_2atr_vs_1atr']=hit
   rec['outcomes'][str(h)]=clean(o)
  rec['predicates']=[dict(label='Known converged bars',value=int(s.N),condition='2–8 BUY / 4–16 SELL',passed=True),dict(label='Episode phase',value=s.phase,condition='Unused; inside or first outside',passed=True),dict(label='Minimum depth so far',value=s.min_depth,condition='Convergence depth ≤0.50',passed=True),dict(label='Current EMA order',value=f'{s.e10:.8f} / {s.e20:.8f} / {s.e50:.8f}',condition='10>20>50 BUY; 10<20<50 SELL',passed=True),dict(label='EMA slopes (10/20/50)',value=f'{s.s10:.8f} / {s.s20:.8f} / {s.s50:.8f}',condition='10/20 strict direction; 50 allows zero',passed=True),dict(label='Width growth',value=float(s.width-f.width.iloc[i-1]),condition='Strictly positive',passed=True),dict(label='Close minus EMA10',value=float(s.close-s.e10),condition='Positive BUY / negative SELL',passed=True),dict(label='Candle body',value=float(s.close-s.open),condition='Positive BUY / negative SELL',passed=True),dict(label='Close location',value=s.cl,condition='≥0.50 BUY / ≤0.50 SELL',passed=True),dict(label='Progression count',value=int(s.up if s.side=='BUY' else s.down),condition='At least 2 of 3 transitions',passed=True),dict(label='Lower high/low pairs',value=int(s.lower),condition='SELL ≥2; BUY has no gate',passed=bool(s.lower>=2) if s.side=='SELL' else None),dict(label='Four contiguous candles',value=bool(s.contig4),condition='Three exact 1800-second intervals',passed=True)]
  entries.append(clean(rec))
 candles=[dict(open_time=str(r.date),close_time=str(r.date+pd.Timedelta(minutes=30)),time=int(r.time),open=r.open,high=r.high,low=r.low,close=r.close,ema10=r.e10,ema20=r.e20,ema50=r.e50,model_atr14=r.atr,model_depth=r.depth) for r in f.itertuples(index=False)]
 last=f.iloc[-1]
 return clean(dict(version='GBPUSD_M30_E1_V0_1',symbol='GBPUSD.pro',point=.00001,pip=.0001,generated_at=now,latest_completed_m30=str(last.date+pd.Timedelta(minutes=30)),quote_broker_time=label(quote) if quote else None,clock='Native broker labels; UTC/EAT conversion unverified',entries=entries,candles=candles,health=dict(refreshed_at=now,state='REPLAY' if not quote else ('SOURCE_LAG' if quote-(last.time+1800)>7200 else 'OK'),last_confirmed_broker_M30=str(last.date+pd.Timedelta(minutes=30))),current=dict(ema_order='BULLISH' if last.e10>last.e20>last.e50 else 'BEARISH' if last.e10<last.e20<last.e50 else 'MIXED',depth=last.depth,converged=bool(last.depth<=.5)),meta=dict(timeframe='M30',period_seconds=1800,paper_only=True,broker_orders_enabled=False,rule='E1 v0.1 unchanged M30 transfer baseline',source_first=str(f.date.iloc[0]),horizons=[12,24],adverse_limit_pips=35,adverse_limit_is_stop=False)))
def main(offline=False):
 config=json.loads((ROOT/'config.json').read_text());assert config['paper_only'] and config['broker_orders_enabled'] is False
 for n,h in config['frozen_hashes'].items():assert sha(ROOT/n)==h,'Frozen file changed: '+n
 base=pd.read_csv(ROOT/'reference/source.csv');raw=base.copy();q=None;revisions=0;entry_hint=None
 if not offline:
  import MetaTrader5 as mt
  assert mt.initialize(),mt.last_error()
  try:
   assert mt.terminal_info().connected,'MT5 disconnected';assert mt.symbol_select('GBPUSD.pro',True)
   tick=mt.symbol_info_tick('GBPUSD.pro');assert tick and tick.time>0
   info=mt.symbol_info('GBPUSD.pro');assert info.point==.00001 and info.digits==5
   q=int(tick.time);rr=mt.copy_rates_from_pos('GBPUSD.pro',mt.TIMEFRAME_M30,0,5000);assert rr is not None and len(rr)>300
   tail=pd.DataFrame(rr);forming=tail[tail.time+1800>q];entry_hint=forming.iloc[0].to_dict() if len(forming) else None;tail=tail[tail.time+1800<=q]
   cache=ROOT/'cache.csv'
   if cache.exists():raw=pd.read_csv(cache)
   common=raw.merge(tail,on='time',suffixes=('_old','_new'));assert len(common)>=24,'Insufficient native overlap'
   for k in ['open','high','low','close']:assert np.allclose(common[k+'_old'],common[k+'_new'],rtol=0,atol=1e-7),'OHLC revision '+k
   revisions=int((common.tick_volume_old!=common.tick_volume_new).sum())
   raw=pd.concat([raw,tail[tail.time>raw.time.max()]],ignore_index=True)
   assert raw.time.iloc[-1]+1800<=q
  finally:mt.shutdown()
 assert len(raw)>=len(base) and np.array_equal(raw.time.iloc[:len(base)].to_numpy(),base.time.to_numpy()),'Frozen cache prefix missing'
 for k in ['open','high','low','close']:assert np.allclose(raw[k].iloc[:len(base)],base[k],rtol=0,atol=1e-7),'Frozen cache prefix altered '+k
 assert raw.time.is_unique and raw.time.is_monotonic_increasing
 assert np.isfinite(raw[['open','high','low','close']]).all().all()
 assert ((raw.low>0)&(raw.low<=raw[['open','close']].min(axis=1))&(raw.high>=raw[['open','close']].max(axis=1))).all()
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();out=project(raw,now,q,entry_hint)
 ref=pd.read_csv(ROOT/'reference/signals.csv');old=[e for e in out['entries'] if e['time']<=base.time.iloc[-1]]
 assert len(old)==len(ref)==109,'Archived signal count changed'
 for e,(_,r) in zip(old,ref.iterrows()):
  assert e['time']==int(pd.Timestamp(r.signal_open_time).timestamp()) and e['direction']==r.side and e['N']==r.N
  for h in (12,24):
   for k in ['gross_pips','mfe_pips','mae_pips']:assert abs(e['outcomes'][str(h)][k]-r[f'h{h}_{k}'])<1e-6
 out['validation']=dict(archived_signals_exact=109,archived_BUY=51,archived_SELL=58,archived_outcomes_exact=218,volume_revisions_ignored_for_ohlc_only_rules=revisions)
 out['meta']['frozen_hashes']=config['frozen_hashes'];out['meta']['source_sha256']=hashlib.sha256(raw.to_csv(index=False).encode()).hexdigest()
 if not offline:
  jp=ROOT/'first_seen.json';seen=json.loads(jp.read_text()) if jp.exists() else {}
  for e in out['entries']:
   seen.setdefault(e['id'],now);e['first_seen_utc']=seen[e['id']];e['origin']='Historical reconstruction; first seen '+seen[e['id']]
  atomic(jp,seen);raw.to_csv(ROOT/'cache.csv',index=False)
 atomic(ROOT/'site/gbpusd-data.json',out)
 if offline:atomic(ROOT/'site/gbpusd-replay.json',out)
 atomic(ROOT/'site/gbpusd-acceptance.json',out['validation'])
 (ROOT/'publication_warning.json').unlink(missing_ok=True)
 print(json.dumps(dict(signals=len(out['entries']),health=out['health'],validation=out['validation'])))
if __name__=='__main__':
 try:main('--offline' in sys.argv)
 except Exception as e:
  atomic(ROOT/'build_error.json',dict(error=str(e),at=datetime.datetime.now(datetime.timezone.utc).isoformat()));raise
