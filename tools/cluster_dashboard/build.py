"""Read-only H1-P1 v2.0 dashboard adapter; never places orders."""
from pathlib import Path
import json,hashlib,datetime,csv,copy
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'source'
def build():
 df=pd.read_csv(BASE/'H1_indicator_ledger.csv');tail=json.loads((ROOT/'latest_native.json').read_text());now=tail['tick']['time'];incoming=pd.DataFrame(tail['bars']);incoming['time_epoch']=incoming.time
 merged=incoming.merge(df,on='time_epoch',suffixes=('_new','_old'));errs={k:float(abs(merged[k+'_new']-merged[k+'_old']).max()) for k in ['open','high','low','close']};assert len(merged)>0 and max(errs.values())<1e-7,errs
 added=incoming[(incoming.time_epoch>df.time_epoch.max())&(incoming.time_epoch+3600<=now)].copy()
 for _,r in added.iterrows():
  prev=df.iloc[-1];rec={k:r[k] for k in ['time_epoch','open','high','low','close','spread']};rec['open_time']=datetime.datetime.fromtimestamp(int(r.time_epoch),datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S');rec['close_time']=datetime.datetime.fromtimestamp(int(r.time_epoch)+3600,datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
  for n in [10,20,50,200]:rec[f'ema{n}']=2/(n+1)*r.close+(1-2/(n+1))*prev[f'ema{n}']
  tr=max(r.high-r.low,abs(r.high-prev.close),abs(r.low-prev.close));rec['wilder_atr14']=(prev.wilder_atr14*13+tr)/14;df=pd.concat([df,pd.DataFrame([rec])],ignore_index=True)
 rows=df.replace({np.nan:None}).to_dict('records');code=(BASE/'engine.py').read_text();ns={'__file__':str(BASE/'engine.py')};exec(compile(code,str(BASE/'engine.py'),'exec'),ns)
 # Original engine parity on the original source window, before adapting I/O cutoff.
 original=rows[:len(df)-len(added)];old=ns['run'](original);expected=json.loads((BASE/'outcomes.json').read_text());assert [(x['entry_time'],x['sgn'],x['entry_price']) for x in old['entries']]==[(x['entry_time'],x['sgn'],x['entry_price']) for x in expected]
 oldout=ns['outcomes'](original,old['entries']);assert all(abs(a['MFE_points']-b['MFE_points'])<1e-6 and abs(a['MAE_points']-b['MAE_points'])<1e-6 and a['end_time']==b['end_time'] for a,b in zip(oldout,expected))
 # Sole live adapter changes: remove historical end-date cutoff; allow current OPEN only.
 assert code.count("'2026-11-09'")==1
 code=code.replace("'2026-11-09'","'9999-12-31'")
 marker="  orders=[]\n  sign=";assert code.count(marker)==1
 code=code.replace(marker,"  orders=[]\n  if r.get('_opening_only'):break\n  sign=")
 live={'__file__':str(BASE/'engine.py')};exec(compile(code,'live_adapter','exec'),live)
 rt=list(rows);forming=incoming[(incoming.time_epoch<=now)&(incoming.time_epoch+3600>now)]
 if len(forming):
  f=forming.iloc[-1];opening=copy.deepcopy(rows[-1]);opening.update(open=float(f.open),open_time=datetime.datetime.fromtimestamp(int(f.time_epoch),datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),_opening_only=True);rt.append(opening)
 decision=live['run'](rt);entries=decision['entries'];out=live['outcomes'](rows,[e for e in entries if e['entry_index']<len(rows)])
 for e in entries:
  if e['entry_index']==len(rows):out.append(dict(**e,cycle_complete=False,target_hit=False,MFE_points=0,MAE_points=0,end_time=e['entry_time'],end_close=e['entry_price'],status='OPEN_NO_COMPLETED_BAR',MFE_bar_close=None))
 clusters={c['case']:c for c in decision['clusters']};public=[]
 for o in out:
  c=clusters[o['case'].rsplit('-',1)[0]];start=o['entry_index'];last=min(len(rows)-1,next((i for i in range(start,len(rows)) if rows[i]['close_time']==o['end_time']),len(rows)-1))
  pub={k:o.get(k) for k in ['case','direction','sgn','entry_time','entry_price','signal_time','cycle_complete','target_hit','MFE_points','MAE_points','end_time','end_close','MFE_bar_close','status']};pub['cluster']=c
  pub['path']=[{'time':o['entry_time'],'price':o['entry_price']}]+[{'time':rows[i]['close_time'],'price':rows[i]['close']} for i in range(start,last+1)]
  pub['peak_price']=o['entry_price']+o['sgn']*o['MFE_points']*.01;public.append(pub)
 last=rows[-1];active=[o for o in public if not o['cycle_complete']];latest_cluster=decision['clusters'][-1];current={'state':'WAIT','direction':None,'reason':'No active qualified entry or pending confirmation.','cluster':latest_cluster,'projection':None}
 if active:
  if len({o['sgn'] for o in active})==1:
   o=active[-1];current.update(state='ACTIVE_CYCLE',direction=o['direction'],sgn=o['sgn'],reason='Qualified H1-P1 v2.0 entry; its EMA10/20 cycle has not ended.',entry=o,cluster=o['cluster'])
  else:current.update(state='MIXED',reason='Opposing research cycles are open. No single projected direction.')
 else:
  pending=[c for c in decision['cases'] if c['status'] in ['WAIT_TWO_CANDLES','WAIT_PRICE_FOLLOW_THROUGH','SIGNAL_AWAITING_OPEN','QUALIFIED_AWAITING_OPEN']]
  if pending:
   c=pending[-1];current.update(state=c['status'],direction=c['direction'],sgn=c['sgn'],reason='Breakout direction only; full v2.0 entry qualification is not yet complete.',cluster=clusters[c['cluster_case']])
 if current.get('sgn'):
  current['projection']={'from_price':last['close'],'illustrative_end_price':last['close']+current['sgn']*last['wilder_atr14'],'note':'Directional guide only. Length and time spacing are illustrative, not a target or forecast horizon.'}
 candles=[{k:r[k] for k in ['open_time','close_time','open','high','low','close','ema10','ema20','ema50','ema200']} for r in rows if r['open_time']>='2025-01-01'];months={}
 for o in public:
  k=o['entry_time'][:7];m=months.setdefault(k,{'entries':0,'hits':0,'misses':0,'open':0});m['entries']+=1;m['open']+=not o['cycle_complete'];m['hits']+=o['cycle_complete'] and o['target_hit'];m['misses']+=o['cycle_complete'] and not o['target_hit']
 payload={'version':'AURUM_CLUSTER_H1_P1_V2_FINAL','symbol':'XAUUSD.pro','timeframe':'H1','point':.01,'benchmark_points':3500,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'quote_observed_at':tail.get('observed_at'),'broker_tick_time':datetime.datetime.fromtimestamp(now,datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),'data_asof':last['close_time'],'refresh_mode':'Snapshot • refreshed on request','current':current,'entries':public,'candles':candles,'months':months,'validation':{'archived_entries_reproduced':len(expected),'archived_outcomes_exact':True,'overlap_bars':len(merged),'max_ohlc_errors':errs,'new_completed_bars':len(added),'forming_candle_excluded':True,'engine_sha256':hashlib.sha256((BASE/'engine.py').read_bytes()).hexdigest()},'rule_summary':['Three of EMA10/20/50/200 within 0.25 preceding ATR','First close outside the fixed cluster box','Two H1 candles with EMA10 and EMA20 moving in direction','Two closes beyond the next-open reference','Following open; one owner per directional EMA10/20 cycle']}
 (ROOT/'site'/'cluster-data.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));(ROOT/'build_receipt.json').write_text(json.dumps(payload['validation'],indent=2));print(json.dumps({'entries':len(public),'current':{k:v for k,v in current.items() if k not in ['entry','cluster']},'asof':last['close_time'],'validation':payload['validation']},indent=2))
 return payload
if __name__=='__main__':build()
