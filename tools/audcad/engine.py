"""AUDCAD frozen BUY/SELL v1.0. Independent OHLC research ledgers, no orders."""
import csv,json,hashlib,math
from pathlib import Path
from datetime import datetime,timezone
PIP=.0001;POINT=.00001;DIST=600
FEED='SCFMLimited-Live2';SYMBOL='AUDCAD.pro'
def stamp(t):return datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def epoch(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
def read_csv(path):
 with open(path,newline='',encoding='utf-8-sig') as f:
  return [dict(time=int(r['time']),**{k:float(r[k]) for k in ('open','high','low','close')}) for r in csv.DictReader(f)]
def validate(raw):
 previous=None
 for b in raw:
  if previous is not None and b['time']<=previous:raise ValueError('Duplicate/unsorted source timestamps')
  if b['time']%1800:raise ValueError('Non-M30 timestamp')
  if not all(math.isfinite(b[k]) and b[k]>0 for k in ('open','high','low','close')):raise ValueError('Invalid price')
  if b['low']>min(b['open'],b['close']) or b['high']<max(b['open'],b['close']) or b['low']>b['high']:raise ValueError('Invalid OHLC')
  previous=b['time']
def candles(raw,cutoff):
 validate(raw);by={b['time']:b for b in raw if b['time']+1800<=cutoff};out=[];rolling=[]
 for t,a in by.items():
  if t%3600 or t+1800 not in by:continue
  z=by[t+1800];b=dict(time=t,open_time=stamp(t),close_time=stamp(t+3600),open=a['open'],high=max(a['high'],z['high']),low=min(a['low'],z['low']),close=z['close'])
  for n in (10,12,20,26,50,200):
   alpha=2/(n+1);b[f'ema{n}']=alpha*b['close']+(1-alpha)*out[-1][f'ema{n}'] if out else b['close']
  b['macd']=b['ema12']-b['ema26'];rolling.append(b['macd']);rolling=rolling[-9:];b['macd_signal']=sum(rolling)/9 if len(rolling)==9 else None;b['histogram']=b['macd']-b['macd_signal'] if b['macd_signal'] is not None else None
  out.append(b)
 return out

def qualifies(b,p,s):
 if b['macd_signal'] is None:return False
 return (s*(b['ema10']-b['ema50'])>0 and s*(p['ema10']-p['ema50'])<=0 and s*(b['ema10']-b['ema20'])>0 and all(s*(b[f'ema{n}']-p[f'ema{n}'])>0 for n in (10,20,50)) and all(s*(b['close']-b[f'ema{n}'])>0 for n in (10,20,50)) and s*b['macd']>0 and s*(b['macd']-p['macd'])>0 and s*(b['macd']-b['macd_signal'])>0)
def points(p):return round(p/POINT)
def outcome(entry,raw,cutoff,s):
 base=points(entry);tp=base+s*DIST;sl=base-s*DIST;status='OPEN';end=None;fav=adv=0;gap=False;observed=[]
 for b in raw:
  if b['time']+1800>cutoff:break
  h,l,o=points(b['high']),points(b['low']),points(b['open']);fav=max(fav,s*((h if s==1 else l)-base));adv=max(adv,-s*((l if s==1 else h)-base));observed.append(b)
  hit_tp=h>=tp if s==1 else l<=tp;hit_sl=l<=sl if s==1 else h>=sl
  if hit_tp or hit_sl:
   status='AMBIGUOUS' if hit_tp and hit_sl else 'TP60' if hit_tp else 'SL60';end=b;gap=s*(o-tp)>0 or s*(o-sl)<0;break
 highest=60.0 if status=='TP60' else fav/10
 return dict(tp_price=tp*POINT,sl_price=sl*POINT,execution_status=status,exit_bar_open=stamp(end['time']) if end else None,exit_bar_available_at=stamp(end['time']+1800) if end else None,gross_pips=60 if status=='TP60' else -60 if status=='SL60' else None,open_mark_pips=s*(points(observed[-1]['close'])-base)/10 if status=='OPEN' and observed else None,highest_pips=highest,movement_success=highest>20,adverse_pips_inclusive=adv/10,gap_flag=gap,observed_bars=len(observed),path=[{'time':stamp(b['time']+1800),'price':b['close']} for b in observed])

def build(raw,cutoff,feed=FEED,symbol=SYMBOL,detected_at=None):
 h1=candles(raw,cutoff);by={b['time']:i for i,b in enumerate(raw) if b['time']<=cutoff};entries=[]
 for i,b in enumerate(h1[1:],1):
  if b['time']<epoch('2026-01-01'):continue
  p=h1[i-1]
  for s,side in ((1,'BUY'),(-1,'SELL')):
   if not qualifies(b,p,s):continue
   t=b['time']+3600;module=f'AUDCAD_H1_{side}_V1_0';key=f'{feed}|{symbol}|{module}|{b["open_time"]}'
   e=dict(id=key,module_id=module,rule_version='1.0',direction=side,sgn=s,signal_bar_open=b['open_time'],signal_available_at=stamp(t),entry_time=stamp(t),detected_at=detected_at,entry_price=None,indicator_snapshot=b,slopes={str(n):b[f'ema{n}']-p[f'ema{n}'] for n in (10,20,50)},price_kind='M30 opening benchmark — not an executed fill',data_quality_state='OK')
   if t not in by:
    pending=not any(x>t for x in by);e.update(execution_status='DATA_PENDING' if pending else 'UNSCORED',reason='Expected M30 entry open not yet available' if pending else 'Missing expected entry bar; never carried to later session',movement_success=None,gross_pips=None,highest_pips=None,open_mark_pips=None,tp_price=None,sl_price=None,exit_bar_open=None,path=[])
   else:
    ix=by[t];e['entry_price']=raw[ix]['open'];e.update(outcome(e['entry_price'],raw[ix:],cutoff,s));e['reason']='All frozen EMA and MACD predicates pass'
   entries.append(e)
 for i,e in enumerate(entries):
  e['overlapping_entry_ids']=[p['id'] for p in entries[:i] if p['entry_price'] is not None and (p.get('exit_bar_available_at') is None or p['exit_bar_available_at']>e['entry_time'])]
 summaries={}
 for side in ('BUY','SELL'):
  rows=[e for e in entries if e['direction']==side];scored=[e for e in rows if e['entry_price'] is not None];counts={k:sum(e['execution_status']==k for e in rows) for k in ('TP60','SL60','OPEN','AMBIGUOUS','UNSCORED','DATA_PENDING')};resolved=counts['TP60']+counts['SL60'];summaries[side]=dict(entries=len(scored),**counts,win_rate=100*counts['TP60']/resolved if resolved else None,movement_successes=sum(bool(e['movement_success']) for e in scored),closed_gross_pips=sum(e['gross_pips'] or 0 for e in rows),open_mark_pips=sum(e['open_mark_pips'] or 0 for e in rows))
 return dict(symbol=symbol,feed=feed,version='AUDCAD_H1_BUY_SELL_V1_0',module_ids=['AUDCAD_H1_BUY_V1_0','AUDCAD_H1_SELL_V1_0'],label='Frozen research baseline — not validated for live trading.',timeframe='H1',point=POINT,pip=PIP,cutoff=stamp(cutoff),latest_completed_h1=h1[-1]['close_time'] if h1 else None,candles=h1,entries=entries,summaries=summaries,source_clock='Original broker timestamps retained without relabelling',costs='Nominal OHLC benchmark barriers. Spread, commission and slippage excluded.',movement_note='Moved >20 pips is descriptive, not break-even execution. TP winners capped at 60; exit-bar extrema may include post-touch prices.',indicator_checkpoint={'last_h1':h1[-1] if h1 else None,'macd_main_last9':[b['macd'] for b in h1[-9:]]})
