"""Frozen GBPJPY entry engine. Broker clock numbers are never converted."""
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path
VERSION='GBPJPY_H1_R1_v1.0'
OVERLAY='GBPJPY_H1_EMA_TOUCH_v1.0'
PIP=.01
START=1790812800 # 2026-10-01 broker clock

def stamp(t):
    return datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M:%S') # formatting only, broker time retained

def indicators(raw, cutoff):
    bars=[]
    for r in raw:
        if r['time']+3600>cutoff: continue
        b={k:r[k] for k in ('time','open','high','low','close')}
        if bars and b['time']<=bars[-1]['time']: raise ValueError('Unsorted/duplicate input bars')
        for n in (10,20):
            a=2/(n+1); b[f'ema{n}']=a*b['close']+(1-a)*bars[-1][f'ema{n}'] if bars else b['close']
        b.update(gap=b['ema10']-b['ema20'],open_time=stamp(b['time']),close_time=stamp(b['time']+3600))
        bars.append(b)
    return bars

def scan(bars,symbol='GBPJPY.pro',start=START):
    candidates=[]; signals=[]; pending=None
    for i,b in enumerate(bars):
        if not i:continue
        p=bars[i-1]
        if pending:
            c=pending;s=c['sgn'];stage=len(c['candles']);fail=[]
            if b['time']-p['time']!=3600:fail.append('missing-hour gap')
            if s*b['gap']<=0:fail.append('EMA ordering')
            for n in (10,20):
                if s*(b[f'ema{n}']-p[f'ema{n}'])<=0:fail.append(f'EMA{n} slope')
            if abs(b['gap'])<=abs(p['gap']):fail.append('gap expansion')
            c['candles'].append(b);c['updated_at']=b['close_time']
            if fail:c.update(state='Rejected',reason=f'C{stage}: '+', '.join(fail));pending=None
            elif stage==2:
                c.update(state='Confirmed '+c['direction'],reason='C1 and C2 passed');pending=None
                signals.append(dict(id=c['id'],direction=c['direction'],sgn=s,decision_time=b['close_time'],entry_time=b['time']+3600,entry_reference=b['close'],entry_kind='C2 close reference — not executed',candles=c['candles'][:],c2_index=i))
            else:c.update(state='C2 pending',reason='C1 passed; awaiting C2 close')
        s=1 if p['gap']<=0 and b['gap']>0 else -1 if p['gap']>=0 and b['gap']<0 else 0
        if s:
            pending=dict(id=f'{VERSION}|{symbol}|H1|{b["open_time"]}',sgn=s,direction='BUY' if s==1 else 'SELL',state='C1 pending',reason='C0 crossed; awaiting C1 close',candles=[b],updated_at=b['close_time'])
            candidates.append(pending)
    return [c for c in candidates if c['candles'][0]['time']>=start],[s for s in signals if s['candles'][0]['time']>=start]

def touch_level(p):
    a=2/11;b=2/21
    return ((1-b)*p['ema20']-(1-a)*p['ema10'])/(a-b)

def evaluate(bars,signal):
    s=signal['sgn'];entry=signal['entry_reference'];future=[];exit=None
    for k in range(signal['c2_index']+1,len(bars)):
        b=bars[k];level=touch_level(bars[k-1]);opening=s*(b['open']-level)<=0
        hit=b['low']<=level if s==1 else b['high']>=level
        if opening or hit:
            price=b['open'] if opening else level
            exit=dict(status='Modeled touch',overlay_version=OVERLAY,bar_open=b['open_time'],bar_close=b['close_time'],time_precision='H1 interval; exact intrabar time unknown',reference_price=price,price_kind='Modeled reference — not executed',method='Opening already crossed' if opening else 'Intrabar equality',gross_pips=s*(price-entry)/PIP)
            break
        future.append(b)
    # Complete bars strictly before touch + exit reference: do not credit post-touch extrema.
    prices=[entry]+[v for b in future for v in (b['high'],b['low'])]+([exit['reference_price']] if exit else [])
    signal.update(exit=exit,MFE_pips=max(0,max(s*(p-entry)/PIP for p in prices)),MAE_pips=max(0,max(-s*(p-entry)/PIP for p in prices)),excursion_basis='Through touch: completed pre-touch candles plus exit reference. Intrabar touch-hour extremes excluded; exact excursion may be larger.',path=[{'time':signal['decision_time'],'price':entry}]+[{'time':b['close_time'],'price':b['close']} for b in future])
    # Modeled exit is a marker, never misrepresented as observed close.
    return signal

def observe(signal,previous_completed,bar_open,tick_time,bid,ask):
    if signal['exit'] or tick_time<signal['entry_time']:return None
    a=2/11;b=2/21;e10=a*bid+(1-a)*previous_completed['ema10'];e20=b*bid+(1-b)*previous_completed['ema20']
    if signal['sgn']*(e10-e20)>0:return None
    return dict(signal_id=signal['id'],overlay_version=OVERLAY,status='Touch observed',broker_time=stamp(tick_time),bar_open=stamp(bar_open),reference_price=bid,ask=ask,spread_pips=(ask-bid)/PIP,ema10=e10,ema20=e20,price_kind='Observed bid reference — not executed',gross_pips=signal['sgn']*(bid-signal['entry_reference'])/PIP,observation_note='First captured tick at/beyond touch. Earlier ticks may be unobserved; not a guaranteed first-market-touch timestamp.')

def build(raw,cutoff,symbol='GBPJPY.pro'):
    bars=indicators(raw,cutoff);candidates,signals=scan(bars,symbol)
    signals=[evaluate(bars,s) for s in signals]
    done=[s for s in signals if s['exit']];wins=sum(s['exit']['gross_pips']>=0 for s in done)
    return dict(version=VERSION,overlay_version=OVERLAY,symbol=symbol,timeframe='H1',point=.001,pip=PIP,label='Frozen research baseline — not validated for live trading.',cutoff=stamp(cutoff),candles=bars,candidates=candidates,signals=signals,candidate=candidates[-1] if candidates else {'state':'Waiting','reason':'No active crossover candidate','candles':[]},summary=dict(signals=len(signals),completed=len(done),open=len(signals)-len(done),nonnegative=wins,losses=len(done)-wins,rate=100*wins/len(done) if done else None,gross_pips=sum(s['exit']['gross_pips'] for s in done)),costs='Spread, commission, swap and slippage not deducted. Gross results only.',executed_prices=None)

if __name__=='__main__':
    root=Path(__file__).resolve().parent;raw=json.loads((root/'frozen_bars.json').read_text());snapshot=build(raw,raw[-1]['time']+3600)
    (root/'gbpjpy-replay.json').write_text(json.dumps(snapshot,indent=2));print(json.dumps(snapshot['summary']))
