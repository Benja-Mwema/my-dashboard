"""Read-only AUDCAD collector with persistent detection/outcome records."""
import json,sqlite3,hashlib,os
from pathlib import Path
from datetime import datetime,timezone
from engine import *
from exit_overlay import attach
ROOT=Path(__file__).resolve().parent

def atomic(p,obj):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(obj,separators=(',',':'),allow_nan=False),encoding='utf-8');t.replace(p)
def persist(d,dbpath,observed,broker_now):
 con=sqlite3.connect(dbpath)
 con.execute('CREATE TABLE IF NOT EXISTS signals (id TEXT PRIMARY KEY, first_detected TEXT NOT NULL, detection_broker_time TEXT NOT NULL, payload TEXT NOT NULL)')
 con.execute('CREATE TABLE IF NOT EXISTS revisions (observed_at TEXT, source_revision TEXT, status TEXT, detail TEXT)')
 con.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, payload TEXT)')
 for e in d['entries']:
  old=con.execute('SELECT first_detected,detection_broker_time FROM signals WHERE id=?',(e['id'],)).fetchone()
  e['detected_at']=old[0] if old else observed;e['detected_broker_time']=old[1] if old else stamp(broker_now)
  e['discovery']='Historical / late discovery' if epoch(e['detected_broker_time'])>epoch(e['signal_available_at'])+60 else 'Observed at scheduled detection'
  e['source_revision']=d['source_revision'];e['rule_config_hash']=d['rule_config_hash']
  con.execute('INSERT INTO signals VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(e['id'],e['detected_at'],e['detected_broker_time'],json.dumps(e)))
 con.execute('INSERT INTO revisions VALUES (?,?,?,?)',(observed,d['source_revision'],'OK','Native overlap matched; immutable seed retained'))
 con.execute('INSERT OR REPLACE INTO state VALUES (?,?)',('indicator_checkpoint',json.dumps(d['indicator_checkpoint'])))
 con.commit();con.close()
def safe_cutoff(native,tick_time):
 # MT5 position zero may still be forming or stale while history synchronizes.
 return min(int(tick_time),native[-1]['time'])

def refresh():
 import MetaTrader5 as mt5
 cfg=json.loads((ROOT/'config.json').read_text())
 if not cfg['enabled']:return {'status':'disabled'}
 frozen=read_csv(ROOT/'source/audcad/AUDCAD_M30_raw_warmup.csv')
 if not mt5.initialize():raise RuntimeError('MT5 unavailable')
 try:
  symbol=cfg['symbol'];mt5.symbol_select(symbol,True);info=mt5.symbol_info(symbol);tick=mt5.symbol_info_tick(symbol);terminal=mt5.terminal_info()
  if info is None or tick is None or terminal is None or not terminal.connected:raise RuntimeError('AUDCAD feed unavailable/disconnected')
  if info.digits!=5 or abs(info.point-POINT)>1e-12:raise RuntimeError('AUDCAD symbol-scale mismatch')
  account=mt5.account_info()
  if account is None or account.server!=FEED:raise RuntimeError('Broker feed identity mismatch')
  rates=mt5.copy_rates_from_pos(symbol,mt5.TIMEFRAME_M30,0,50000)
  if rates is None:raise RuntimeError('M30 retrieval failed')
  native=[dict(time=int(r['time']),**{k:float(r[k]) for k in ('open','high','low','close')}) for r in rates]
  validate(native);cache=ROOT/'native_tail.json';saved=json.loads(cache.read_text()) if cache.exists() else []
  # Persist only completed bars. A forming bar can revise legitimately.
  history=frozen+saved;by={b['time']:b for b in history};overlap=0
  for b in native:
   old=by.get(b['time'])
   if old:
    overlap+=1
    if any(points(old[k])!=points(b[k]) for k in ('open','high','low','close')):
     atomic(ROOT/'data_quality.json',{'status':'SOURCE_REVISION_BLOCKED','broker_time':stamp(int(tick.time)),'revised_bar':stamp(b['time']),'previous':old,'new':b})
     raise RuntimeError('Source revision detected; retained historical data, publication blocked')
  if overlap<24:raise RuntimeError('Insufficient native overlap for safe continuation')
  fresh=[b for b in native if b['time']>history[-1]['time']]
  if fresh and fresh[0]['time']>history[-1]['time']+1800 and history[-1]['time']<native[0]['time']:raise RuntimeError('Native backfill window cannot cover history')
  raw=history+fresh;now=int(tick.time);completed_cutoff=safe_cutoff(native,now);d=build(raw,completed_cutoff,FEED,symbol);attach(d,raw,completed_cutoff)
  observed=datetime.now(timezone.utc).isoformat();d.update(generated_at=observed,quote_broker_time=stamp(now),quote_bid=tick.bid,source_revision=hashlib.sha256(json.dumps([b for b in raw if b['time']+1800<=completed_cutoff],separators=(',',':')).encode()).hexdigest(),rule_config_hash=hashlib.sha256((ROOT/'source/AUDCAD_H1_BUY_Frozen_Rule_v1_0.md').read_bytes()+(ROOT/'source/AUDCAD_H1_SELL_Frozen_Rule_v1_0.md').read_bytes()).hexdigest(),native_overlap_verified=overlap,completed_source_cutoff=stamp(completed_cutoff),forming_bar_open=stamp(native[-1]['time']),data_quality_state='OK',publication_mode='Shared 15-minute snapshot publication; not streaming')
  persist(d,ROOT/'signals.sqlite',observed,now)
  atomic(cache,[b for b in raw if b['time']>frozen[-1]['time'] and b['time']+1800<=completed_cutoff])
  atomic(ROOT/'audcad-data.json',d);atomic(ROOT/'data_quality.json',{'status':'OK','broker_time':stamp(now)});print(json.dumps({'asof':d['latest_completed_h1'],'summary':d['summaries']}));return d
 finally:mt5.shutdown()
if __name__=='__main__':refresh()
