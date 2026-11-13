"""User-authorized retracement overlay; frozen entry/exit baseline stays intact."""
from engine import points,epoch,stamp,POINT
VERSION='AUDCAD_EXIT_RETRACE50_V1_0'
def evaluate(e,bars,cutoff,opposite_times):
 if e['entry_price'] is None:return dict(version=VERSION,status=e['execution_status'],gross_pips=None,reason=e['reason'],turns=[])
 s=e['sgn'];base=points(e['entry_price']);start=epoch(e['entry_time']);peak=0;peak_time=None;mode='NORMAL';turns=[];status='OPEN';exit_price=None;exit_time=None;gap=False;last_profit=0
 for b in bars:
  if b['time']<start:continue
  # An opposing confirmation is known at this opening event; no forming high/low used.
  if b['time']>cutoff:break
  op=s*(points(b['open'])-base)
  if op>=600:status='TP60';exit_price=base+s*600;gap=op>600
  elif op<=-600:status='SL60';exit_price=base-s*600;gap=op< -600
  elif mode=='BE_ARMED' and op<=0:
   status='BE' if op==0 else 'BE_GAP';exit_price=points(b['open']);gap=op<0
  elif mode=='EARLY_TURN' and b['time'] in opposite_times:
   status='OPPOSITE';exit_price=points(b['open'])
  if exit_price is not None:exit_time=b['time'];break
  if b['time']+1800>cutoff:break
  hi=s*(points(b['high'] if s==1 else b['low'])-base);lo=s*(points(b['low'] if s==1 else b['high'])-base);cl=s*(points(b['close'])-base)
  hit_tp=hi>=600;hit_sl=lo<=-600;hit_be=mode=='BE_ARMED' and lo<=0
  if (hit_tp and (hit_sl or hit_be)):
   status='AMBIGUOUS';exit_time=b['time']+1800;break
  if hit_tp:status='TP60';exit_price=base+s*600
  elif hit_be:status='BE';exit_price=base
  elif hit_sl:status='SL60';exit_price=base-s*600
  if exit_price is not None:exit_time=b['time']+1800;break
  if hi>peak:peak=hi;peak_time=b['time']
  # Strict >50% retracement. At zero favorable excursion, a negative close is early failure.
  if cl*2<peak and (mode=='NORMAL' or (mode=='EARLY_TURN' and peak>=200)):
   mode='BE_ARMED' if peak>=200 else 'EARLY_TURN'
   turns.append(dict(confirmed_at=stamp(b['time']+1800),bar_open=stamp(b['time']),turn_price=b['close'],peak_price=(base+s*peak)*POINT,peak_pips=peak/10,peak_bar=stamp(peak_time) if peak_time is not None else None,retracement_pips=(peak-cl)/10,mode=mode))
   if mode=='BE_ARMED' and cl<0:
    status='AMBIGUOUS_BE_ACTIVATION';exit_time=b['time']+1800;break
   if mode=='BE_ARMED' and cl==0:
    status='BE';exit_price=base;exit_time=b['time']+1800;break
  last_profit=cl
 if status=='TP60':peak=max(peak,600)
 return dict(version=VERSION,status=status,exit_time=stamp(exit_time) if exit_time is not None else None,exit_price=exit_price*POINT if exit_price is not None else None,gross_pips=s*(exit_price-base)/10 if exit_price is not None else None,open_mark_pips=last_profit/10 if status=='OPEN' else None,mode=mode,turns=turns,gap_flag=gap,peak_before_exit_pips=peak/10,price_kind='Research reference, not executed',reason='Completed M30 close confirms >50% retracement. BE activates prospectively; opposite confirmation exits only the early-turn branch.')
def attach(snapshot,raw,cutoff):
 opposite={side:{epoch(e['signal_available_at']) for e in snapshot['entries'] if e['direction']!=side} for side in ('BUY','SELL')}
 for e in snapshot['entries']:
  o=evaluate(e,raw,cutoff,opposite[e['direction']]);e['exit_overlay']=o
  o['path']=[{'time':stamp(b['time']+1800),'price':b['close']} for b in raw if e['entry_price'] is not None and b['time']>=epoch(e['entry_time']) and b['time']+1800<=cutoff and (not o.get('exit_time') or stamp(b['time']+1800)<o['exit_time'])]
 snapshot['exit_overlay_version']=VERSION
 snapshot['exit_overlay_note']='Turn: completed M30 close retraces strictly more than 50% of running maximum favorable movement. At least 20 and below 60 arms BE; below 20 enables opposite-confirmation exit. TP60/SL60 remain barriers. BE gaps and same-bar uncertainty are explicit. Post-TP chart movement is not profit.'
 return snapshot
