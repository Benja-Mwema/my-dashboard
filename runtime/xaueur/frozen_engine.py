from pathlib import Path
import csv,json,itertools,hashlib,copy,datetime,collections
P=Path(__file__).resolve().parent
TRIOS=list(itertools.combinations((10,20,50,200),3))
def dump(n,x):(P/n).write_text(json.dumps(x,indent=2,allow_nan=False))
def load():
 rows=list(csv.DictReader((P/'source/H1_indicator_ledger.csv').open()))
 for r in rows:
  for k in ['open','high','low','close','ema10','ema20','ema50','ema200','wilder_atr14','spread']:r[k]=float(r[k]) if r[k] else None
 return rows
def run(rows):
 clusters=[];cases=[];events=[];entries=[];orders=[];pending=[];active=None;prev_tight=False;cycle=0;old_sign=0;owners={};references=[];watch=[]
 def emit(kind,i,**kw):events.append(dict(kind=kind,observed_index=i,**copy.deepcopy(kw)))
 for i,r in enumerate(rows):
  prev=rows[i-1] if i else None
  for ci in references:
   c=cases[ci]
   c.update(reference_price=r['open'],reference_index=i,reference_time=r['open_time'],ema_signal_time=c['signal_time'],ema_signal_index=c['signal_index'],price_checks=[],status='WAIT_PRICE_FOLLOW_THROUGH')
   watch.append(ci);emit('REFERENCE',i,time=r['open_time'],case=c['case'],price=r['open'])
  references=[]
  # Opening execution uses only the previous completed candle's signal.
  for order in orders:
   c=cases[order['case_index']]
   if c['sgn'] in owners:
    c.update(status='DUPLICATE_CYCLE',duplicate_of=owners[c['sgn']]['case'])
    emit('DUPLICATE',i,time=r['open_time'],case=c['case'],duplicate_of=c['duplicate_of'])
   else:
    aligned=old_sign==c['sgn']
    key=f'{c["sgn"]}:cycle{cycle}' if aligned else f'{c["sgn"]}:await@{i}'
    ent=dict(case=c['case'],direction=c['direction'],sgn=c['sgn'],signal_time=c['signal_time'],signal_index=c['signal_index'],entry_time=r['open_time'],entry_index=i,entry_price=r['open'],cycle=key,aligned_at_entry=aligned,entry_gap_from_signal_price=r['open']-prev['close'],entry_wait_hours=(datetime.datetime.fromisoformat(r['open_time'])-datetime.datetime.fromisoformat(c['signal_time'])).total_seconds()/3600,entry_bar_reported_spread_points=r['spread'],spread_note='Reported spread belongs to the aggregated H1 source bar, not a verified opening bid/ask quote.',slippage=None,commission=None)
    entries.append(ent);owners[c['sgn']]=dict(case=c['case'],aligned=aligned,entry_key=key);c.update(status='ENTRY',entry=copy.deepcopy(ent))
    emit('ENTRY',i,**ent)
  orders=[]
  sign=1 if r['ema10']>r['ema20'] else -1 if r['ema10']<r['ema20'] else 0
  if sign!=old_sign:cycle+=1
  old_sign=sign
  for sg,owner in list(owners.items()):
   if not owner['aligned'] and sign==sg:
    owner['aligned']=True;emit('CYCLE_ESTABLISHED',i,time=r['close_time'],case=owner['case'],direction=sg,established_cycle=cycle)
   elif owner['aligned'] and sign!=sg:
    emit('CYCLE_FINISHED',i,time=r['close_time'],case=owner['case'],direction=sg);del owners[sg]
  gap=prev is None or r['open_time']!=prev['close_time']
  width,trio=min((max(r[f'ema{n}'] for n in t)-min(r[f'ema{n}'] for n in t),t) for t in TRIOS)
  atr=prev['wilder_atr14'] if prev else None
  tight=bool(atr and width/atr<=.25+1e-9)
  start=tight and (gap or not prev_tight);prev_tight=tight
  if not '2025-01-01'<=r['open_time'][:10]<='2026-11-09':continue
  # Each direction is consumed once; attempts persist independently.
  if active is not None:
   box=clusters[active];sgn=1 if r['close']>box['high'] else -1 if r['close']<box['low'] else 0
   if sgn and sgn not in box['seen']:
    direction='UP' if sgn==1 else 'DOWN'
    c=dict(case=box['case']+'-'+direction,cluster_case=box['case'],attempt_order=len(box['seen'])+1,low=box['low'],high=box['high'],first_break=r['close_time'],break_index=i,break_close=r['close'],direction=direction,sgn=sgn,status='WAIT_TWO_CANDLES',checks=[])
    box['seen'].append(sgn);cases.append(c)
    pending.append(len(cases)-1);emit('FIRST_BREAK',i,time=r['close_time'],case=c['case'],direction=direction,close=r['close'])
  remaining=[]
  for ci in pending:
   c=cases[ci];age=i-c['break_index']
   if age in (1,2):
    checks={str(n):c['sgn']*(r[f'ema{n}']-prev[f'ema{n}'])>0 for n in (10,20)}
    c['checks'].append(dict(time=r['close_time'],source_index=i,gap=gap,EMA10_change=r['ema10']-prev['ema10'],EMA20_change=r['ema20']-prev['ema20'],checks=checks))
    emit('PERSISTENCE_OBSERVATION',i,time=r['close_time'],case=c['case'],age=age,checks=checks,gap=gap)
   if age==2:
    passed=all(v for a in c['checks'] for v in a['checks'].values())
    c.update(persistence_pass=passed,decision_time=r['close_time'],signal_index=i)
    if passed:
     c.update(status='SIGNAL_AWAITING_OPEN',signal_time=r['close_time'],cycle=cycle)
     references.append(ci)
    else:c['status']='NO_SIGNAL'
    emit('SIGNAL' if passed else 'NO_SIGNAL',i,time=r['close_time'],case=c['case'],cycle=cycle)
   else:remaining.append(ci)
  pending=remaining
  remaining_watch=[]
  for ci in watch:
   c=cases[ci];age=i-c['reference_index']
   if age in (0,1):
    move=c['sgn']*(r['close']-c['reference_price']);passed=move>0
    check=dict(time=r['close_time'],source_index=i,close=r['close'],directional_points=move*100,passed=passed,gap=gap)
    c['price_checks'].append(check);emit('PRICE_OBSERVATION',i,case=c['case'],**check)
   if age==1:
    passed=all(z['passed'] for z in c['price_checks'])
    c.update(followthrough_pass=passed,followthrough_decision_time=r['close_time'])
    if passed:
     c.update(status='QUALIFIED_AWAITING_OPEN',signal_time=r['close_time'],signal_index=i)
     orders.append(dict(case_index=ci,cycle=cycle))
    else:c['status']='PRICE_REJECT'
    emit('QUALIFIED' if passed else 'PRICE_REJECT',i,time=r['close_time'],case=c['case'])
   else:remaining_watch.append(ci)
  watch=remaining_watch
  if start:
   c=dict(case=f'Y{len(clusters)+1:03d}',detected_at=r['close_time'],detected_index=i,trio=list(trio),width=width,width_ATR=width/atr,low=r['low'],high=r['high'],seen=[])
   clusters.append(c);active=len(clusters)-1;emit('CLUSTER',i,time=r['close_time'],case=c['case'])
 return dict(clusters=clusters,cases=cases,events=events,entries=entries)

def outcomes(rows,entries):
 out=[]
 for e in entries:
  s=e['sgn'];start=e['entry_index'];end=None;aligned=e['aligned_at_entry'];alignment_index=start-1 if aligned else None
  for j in range(start,len(rows)):
   gap=s*(rows[j]['ema10']-rows[j]['ema20'])
   if not aligned and gap>0:aligned=True;alignment_index=j
   elif aligned and gap<=0:end=j;break
  stop=end if end is not None else len(rows)-1
  path=rows[start:stop+1];target=e['entry_price']+s*35
  hit=next((j for j in range(start,stop+1) if (rows[j]['high']>=target if s==1 else rows[j]['low']<=target)),None)
  fav=[s*((r['high'] if s==1 else r['low'])-e['entry_price'])*100 for r in path]
  adv=[-s*((r['low'] if s==1 else r['high'])-e['entry_price'])*100 for r in path]
  out.append(dict(**e,alignment_known_at=rows[alignment_index]['close_time'] if alignment_index is not None else None,target_price=target,target_hit=hit is not None,target_bar_open=rows[hit]['open_time'] if hit is not None else None,target_known_by=rows[hit]['close_time'] if hit is not None else None,target_same_bar_as_cross=hit is not None and hit==end,target_elapsed_hours_upper_bound=(datetime.datetime.fromisoformat(rows[hit]['close_time'])-datetime.datetime.fromisoformat(e['entry_time'])).total_seconds()/3600 if hit is not None else None,cycle_complete=end is not None,end_time=rows[stop]['close_time'],end_close=rows[stop]['close'],MFE_points=max(0,max(fav)),MAE_points=max(0,max(adv)),MFE_bar_close=path[fav.index(max(fav))]['close_time'],MAE_bar_close=path[adv.index(max(adv))]['close_time'],remaining_points=s*(rows[stop]['close']-e['entry_price'])*100,status='TARGET_HIT' if hit is not None else 'TARGET_MISS_AT_CROSS' if end is not None else 'OPEN_NO_TARGET_YET',bars_observed=len(path),source_gaps=sum(rows[j]['open_time']!=rows[j-1]['close_time'] for j in range(start,stop+1))))
 return out

# Run run_extended.py for the extended evaluation and verification.
