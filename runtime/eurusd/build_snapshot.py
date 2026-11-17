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
  i=int(s.i);rec=clean(s.to_dict());rec.update(id=f"EURUSD_E2S_M30_{int(s.time)}_{s.side}",direction=s.side,signal_bar_open=str(s.date),signal_available_at=str(s.decision),entry_time=None,entry_price=None,entry_status='PENDING_ENTRY',origin='Historical reconstruction',outcomes={})
  if i+1<len(f):
   if f.time.iloc[i+1]-s.time!=1800:rec['entry_status']='CANCELLED_GAP'
   else:rec.update(entry_status='ENTERED',entry_time=str(f.date.iloc[i+1]),entry_price=float(f.open.iloc[i+1]))
  elif entry_hint is not None:
   if entry_hint['time']-s.time==1800:rec.update(entry_status='ENTERED',entry_time=label(entry_hint['time']),entry_price=float(entry_hint['open']))
   elif entry_hint['time']>s.time+1800:rec['entry_status']='CANCELLED_GAP'
  for h in (6,12,24):
   o=dict(status=rec['entry_status'] if rec['entry_status']!='ENTERED' else 'PENDING_OUTCOME',gross_pips=None,mfe_pips=None,mae_pips=None,end_time=None,end_price=None,forward_gap=None)
   if rec['entry_status']=='ENTERED':
    w=f.iloc[i+1:min(i+h+1,len(f))];E=rec['entry_price'];d=1 if s.side=='BUY' else -1
    if len(w):
     mfe=max(0,w.high.max()-E) if d==1 else max(0,E-w.low.min());mae=max(0,E-w.low.min()) if d==1 else max(0,w.high.max()-E)
     o.update(observed_bars=len(w),partial_mfe_pips=round(mfe/.0001,8),partial_mae_pips=round(mae/.0001,8),mark_pips=round(d*(w.close.iloc[-1]-E)/.0001,8),forward_gap=bool(w.time.diff().dropna().ne(1800).any()))
    if len(w)==h:
     gross=d*(int(round(w.close.iloc[-1]/.00001))-int(round(E/.00001)))/10;maep=round(mae/.0001,8)
     o.update(status='COMPLETE',gross_pips=gross,net2_pips=round(gross-2,8),mfe_pips=round(mfe/.0001,8),mae_pips=maep,end_time=str(w.date.iloc[-1]+pd.Timedelta(minutes=30)),end_price=float(w.close.iloc[-1]),mfe_atr=mfe/s.atr,mae_atr=mae/s.atr)
   if o['status']=='COMPLETE':
    fav=E+d*2*s.atr;adv=E-d*s.atr;hit='unresolved'
    for z in w.itertuples(index=False):
     hf=z.high>=fav if d==1 else z.low<=fav;ha=z.low<=adv if d==1 else z.high>=adv
     if hf or ha:hit='ambiguous' if hf and ha else 'favorable_first' if hf else 'adverse_first';break
    o['first_hit_2atr_vs_1atr']=hit
   rec['outcomes'][str(h)]=clean(o)
  def pred(name,value,condition,passed):return dict(label=name,value=clean(value),condition=condition,passed=bool(passed))
  rec['predicates']=[
   pred('EMA20 / EMA50 / EMA200',f'{s.e20:.8f} / {s.e50:.8f} / {s.e200:.8f}','20 < 50 < 200',s.e20<s.e50<s.e200),
   pred('Slopes S20 / S50 / S200',f'{s.s20:.8f} / {s.s50:.8f} / {s.s200:.8f}','S20 < 0; S50 < 0; S200 <= 0',s.s20<0 and s.s50<0 and s.s200<=0),
   pred('EMA20–50 band / ATR',s.band20_50,'0.25 <= band <= 2',.25<=s.band20_50<=2),
   pred('Pullback episode',label(int(s.episode_id)),'Active unused episode; new touch follows close below EMA20',True),
   pred('Bars since qualifying touch',s.bars_since_touch,'<= 3 bars',s.bars_since_touch<=3),
   pred('Signal cooldown distance',s.cooldown_distance,'> 12 positions; gap resets state',s.cooldown_distance>12),
   pred('Six contiguous candles',s.contig6,'Five exact 1800-second intervals',s.contig6),
   pred('Bearish body / ATR',s.body_atr,'Close < Open; body >= 0.4 ATR',s.close<s.open and s.body_atr>=.4),
   pred('Close location',s.cl,'Lower 35%; research compares 1-CL >= 0.65',1-s.cl>=.65),
   pred('Previous close / EMA10',f'{s.prior_close:.8f} / {s.prior_e10:.8f}','Previous close >= previous EMA10',s.prior_close>=s.prior_e10),
   pred('Close / EMA10',f'{s.close:.8f} / {s.e10:.8f}','Current close < EMA10',s.close<s.e10),
   pred('Extension below EMA20 / ATR',s.extension20_atr,'0 < extension <= 1.0',0<s.extension20_atr<=1)]
  entries.append(clean(rec))
 candles=[dict(open_time=str(r.date),close_time=str(r.date+pd.Timedelta(minutes=30)),time=int(r.time),open=r.open,high=r.high,low=r.low,close=r.close,ema10=r.e10,ema20=r.e20,ema50=r.e50,ema200=r.e200,model_atr14=r.atr,model_depth=r.depth) for r in f.itertuples(index=False)]
 last=f.iloc[-1]
 return clean(dict(version='EURUSD_M30_E2S_V0_2',symbol='EURUSD.pro',point=.00001,pip=.0001,generated_at=now,latest_completed_m30=str(last.date+pd.Timedelta(minutes=30)),quote_broker_time=label(quote) if quote else None,clock='Native broker labels; UTC/EAT conversion unverified',entries=entries,candles=candles,health=dict(refreshed_at=now,state='REPLAY' if not quote else ('SOURCE_LAG' if quote-(last.time+1800)>1800 else 'OK'),last_confirmed_broker_M30=str(last.date+pd.Timedelta(minutes=30))),current=dict(ema_order='BULLISH' if last.e10>last.e20>last.e50 else 'BEARISH' if last.e10<last.e20<last.e50 else 'MIXED',depth=last.depth,converged=bool(last.depth<=.5)),meta=dict(timeframe='M30',period_seconds=1800,paper_only=True,broker_orders_enabled=False,rule='E2-S v0.2 / F162 SELL pullback research candidate',validation_status='LATER_CONSISTENCY_GATE_FAILED',source_first=str(f.date.iloc[0]),horizons=[6,12,24],primary_horizon=12,cost_stress_pips=2,cost_is_hypothetical=True)))
def main(offline=False):
 config=json.loads((ROOT/'config.json').read_text());assert config['paper_only'] and config['broker_orders_enabled'] is False
 for n,h in config['frozen_hashes'].items():assert sha(ROOT/n)==h,'Frozen file changed: '+n
 base=pd.read_csv(ROOT/'reference/source.csv');raw=base.copy();q=None;revisions=0;entry_hint=None
 if not offline:
  import MetaTrader5 as mt
  assert mt.initialize(),mt.last_error()
  try:
   assert mt.terminal_info().connected,'MT5 disconnected';assert mt.symbol_select('EURUSD.pro',True)
   tick=mt.symbol_info_tick('EURUSD.pro');assert tick and tick.time>0
   info=mt.symbol_info('EURUSD.pro');assert info.point==.00001 and info.digits==5
   q=int(tick.time);rr=mt.copy_rates_from_pos('EURUSD.pro',mt.TIMEFRAME_M30,0,5000);assert rr is not None and len(rr)>300
   tail=pd.DataFrame(rr).sort_values('time');entry_hint=tail.iloc[-1].to_dict();tail=tail.iloc[:-1];tail=tail[tail.time+1800<=q] # Exclude final native bar even when feed lags.
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
 assert len(old)==len(ref)==53,'Archived signal count changed'
 count=0
 for e,(_,r) in zip(old,ref.iterrows()):
  assert e['time']==int(r.time) and e['direction']==r.side and e['episode_id']==r.episode_id
  for k in ['atr','e10','e20','e50','e200','depth','body_atr','extension20_atr','band20_50']:assert abs(e[k]-r[k])<1e-12,'Feature mismatch '+k
  assert e['entry_status']==r.entry_status.upper()
  assert all(p['passed'] for p in e['predicates'])
  for h in (6,12,24):
   o=e['outcomes'][str(h)];assert o['status']==r[f'h{h}_status'].upper()
   if o['status']=='COMPLETE':
    for k in ['gross_pips','mfe_pips','mae_pips']:assert abs(o[k]-r[f'h{h}_{k}'])<1e-6
    assert o['end_time']==r[f'h{h}_endpoint_label'] and o['forward_gap']==r[f'h{h}_forward_gap']
    count+=1
 assert count==156
 out['validation']=dict(archived_signals_exact=53,archived_BUY=0,archived_SELL=53,archived_outcomes_exact=156,cancelled_entries=1,volume_revisions_ignored_for_ohlc_only_rules=revisions)
 out['meta']['frozen_hashes']=config['frozen_hashes'];out['meta']['source_sha256']=hashlib.sha256(raw.to_csv(index=False).encode()).hexdigest()
 if not offline:
  jp=ROOT/'first_seen.json';seen=json.loads(jp.read_text()) if jp.exists() else {}
  for e in out['entries']:
   seen.setdefault(e['id'],now);e['first_seen_utc']=seen[e['id']];e['origin']='Historical reconstruction; first seen '+seen[e['id']]
  atomic(jp,seen);raw.to_csv(ROOT/'cache.csv',index=False)
 atomic(ROOT/'site/eurusd-data.json',out)
 if offline:atomic(ROOT/'site/eurusd-replay.json',out)
 atomic(ROOT/'site/eurusd-acceptance.json',out['validation'])
 (ROOT/'publication_warning.json').unlink(missing_ok=True);(ROOT/'build_error.json').unlink(missing_ok=True)
 print(json.dumps(dict(signals=len(out['entries']),health=out['health'],validation=out['validation'])))
if __name__=='__main__':
 try:main('--offline' in sys.argv)
 except Exception as e:
  atomic(ROOT/'build_error.json',dict(error=str(e),at=datetime.datetime.now(datetime.timezone.utc).isoformat()));raise
