"""Manual, read-only MT5 snapshot refresh. No scheduler, publisher or trade API."""
from pathlib import Path
import json,datetime
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parent
if not mt5.initialize():raise RuntimeError('MT5 unavailable: '+str(mt5.last_error()))
try:
 info=mt5.symbol_info('XAUUSD.pro');tick=mt5.symbol_info_tick('XAUUSD.pro')
 if info is None or tick is None:raise RuntimeError('XAUUSD.pro unavailable')
 if abs(info.point-.01)>1e-12:raise RuntimeError('Unexpected point size')
 rates=mt5.copy_rates_from_pos('XAUUSD.pro',mt5.TIMEFRAME_H1,0,20000)
 if rates is None or len(rates)<100:raise RuntimeError('Insufficient native H1')
 payload={'point':info.point,'digits':info.digits,'tick':tick._asdict(),'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bars':[{k:float(v) if k in ['open','high','low','close'] else int(v) for k,v in zip(rates.dtype.names,z)} for z in rates if int(z['time'])>=1793664000]}
 # Never silently label a disconnected terminal's old quote current.
 last=int(rates[-1]['time']);assert tick.time>=last
 (ROOT/'latest_native.json').write_text(json.dumps(payload))
finally:mt5.shutdown()
from build import build
build()
