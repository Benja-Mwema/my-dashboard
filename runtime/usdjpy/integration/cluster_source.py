"""Completed H1 formations used by the AURUM dashboard alert worker."""
from bisect import bisect_right
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
import csv
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build_market_context as market

SITE = market.REPO
HOUR = 3600
CHART = "Dashboard EMA10/20/50 v1"
GBPUSD_CROSS = "GBPUSD H1 EMA10/20 cross v2"
GOLD = "Gold H1-P1 v2.0"
TRIOS = tuple(combinations((10, 20, 50, 200), 3))


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def epoch(value):
    if isinstance(value, (float, int)):
        return int(value)
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def label(value):
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def bar(raw):
    if isinstance(raw, list):
        raw = dict(zip(("time", "open", "high", "low", "close", "ema20", "ema50"), raw))
    return {**raw, "time": epoch(raw.get("open_time", raw.get("time")))}


def hours(rows, is_m30):
    if not is_m30:
        return rows
    result = []
    first = None
    for row in rows:
        if row["time"] % HOUR == 0:
            first = row
        elif first and row["time"] == first["time"] + 1800:
            result.append(dict(time=first["time"], open=first["open"],
                               high=max(first["high"], row["high"]),
                               low=min(first["low"], row["low"]), close=row["close"]))
            first = None
    return result


def true_range(b, previous):
    return max(b["high"] - b["low"], abs(b["high"] - previous), abs(b["low"] - previous))


def formation(b, model, trio, width, atr):
    return dict(at=b["time"] + HOUR, model=model, trio=list(trio), ratio=width / atr,
                low=b["low"], high=b["high"])


def watch_at_detection(close, current, previous):
    data = dict(side="WAIT", close=close, ema10=current[0], ema20=current[1])
    if previous is None or any(x is None for x in (*current[:2], *previous[:2])):
        return dict(data, reason="history")
    fast, slow = current[:2]
    old_fast, old_slow = previous[:2]
    data.update(previous_ema10=old_fast, previous_ema20=old_slow, reason="mixed")
    if close > max(fast, slow) and fast > old_fast and slow > old_slow:
        data.update(side="BUY", reason="rising")
    elif close < min(fast, slow) and fast < old_fast and slow < old_slow:
        data.update(side="SELL", reason="falling")
    return data


def chart_boxes(rows, watch=None, require_cross=False):
    # Matches aurum-charts-v3.js derive(): supplied EMAs take precedence for
    # this bar only. The chart maintains its separate recursive EMA history.
    result, emas, seed = [], {}, []
    active = atr = previous = prior_values = prior_time = None
    last_order = 0
    cross_at = None
    for i, b in enumerate(rows):
        close = b["close"]
        prior_atr = atr
        tr = b["high"] - b["low"] if previous is None else true_range(b, previous)
        if i < 14:
            seed.append(tr)
            if i == 13:
                atr = sum(seed) / 14
        else:
            atr = (atr * 13 + tr) / 14
        values = []
        for p in (10, 20, 50):
            emas[p] = close if not i else emas[p] + 2 / (p + 1) * (close - emas[p])
            value = b.get(f"ema{p}")
            values.append(value if isinstance(value, (int, float)) and math.isfinite(value)
                          else emas[p] if i >= 250 else None)
        at = b["time"] + HOUR
        order = 0
        if require_cross:
            if prior_time != b["time"] - HOUR or None in values[:2]:
                last_order, cross_at = 0, None
            if None not in values[:2]:
                order = (values[0] > values[1]) - (values[0] < values[1])
                if order and last_order and order != last_order:
                    cross_at = at
                if order:
                    last_order = order
        if active:
            side = 1 if close > active["high"] else -1 if close < active["low"] else 0
            if side and (not require_cross or
                         (cross_at is not None and cross_at >= active["at"] and order == side)):
                if require_cross:
                    active["confirmation"] = dict(at=at, crossed_at=cross_at, close=close,
                                                  side="BUY" if side == 1 else "SELL")
                active = None
        formed = False
        if not active and prior_atr and prior_atr > 0 and None not in values:
            width = max(values) - min(values)
            if width / prior_atr <= 0.25:
                active = formation(b, GBPUSD_CROSS if require_cross else CHART, (10, 20, 50), width, prior_atr)
                result.append(active)
                formed = True
        if watch is not None and (formed or at in watch):
            adjacent = prior_time is not None and b["time"] == prior_time + HOUR
            watch[at] = watch_at_detection(close, values, prior_values if adjacent else None)
        prior_values, prior_time = values, b["time"]
        previous = close
    return result


def gold_boxes(rows):
    # Resume at the exact frozen ledger boundary, including its prior tight state.
    with (ROOT / "source/H1_indicator_ledger.csv").open(encoding="utf-8-sig", newline="") as fh:
        previous, last = None, None
        for item in csv.DictReader(fh):
            previous, last = last, item
    t = int(last["time_epoch"])
    join = next((r for r in rows if r["time"] == t), None)
    if join is None or any(abs(join[k] - float(last[k])) > 1e-7 for k in ("open","high","low","close")):
        raise ValueError("Gold frozen ledger does not join the dashboard candle history")
    emas = {p: float(last[f"ema{p}"]) for p in (10, 20, 50, 200)}
    def narrowest():
        return min((max(emas[p] for p in trio) - min(emas[p] for p in trio), trio) for trio in TRIOS)
    width, _ = narrowest()
    tight = width / float(previous["wilder_atr14"]) <= 0.25 + 1e-9
    atr, close = float(last["wilder_atr14"]), float(last["close"])
    result = []
    for b in rows:
        if b["time"] <= t:
            continue
        for p in emas:
            alpha = 2 / (p + 1)
            emas[p] = alpha * b["close"] + (1 - alpha) * emas[p]
        width, trio = narrowest()
        now_tight = atr > 0 and width / atr <= 0.25 + 1e-9
        if now_tight and (not tight or b["time"] != t + HOUR):
            result.append(formation(b, GOLD, trio, width, atr))
        atr = (13 * atr + true_range(b, close)) / 14
        tight, close, t = now_tight, b["close"], b["time"]
    return result


def native_bridge(asset, history):
    # The chart publisher holds its prior snapshot on a revised native bar.
    # Bridge only the specifically reconciled close. Any other mismatch fails.
    import MetaTrader5 as mt
    symbol = asset['symbol']
    half = asset['timeframe'] == 'M30'
    step = 1800 if half else HOUR
    if not mt.initialize():
        raise RuntimeError(str(mt.last_error()))
    try:
        if not mt.terminal_info().connected:
            raise ValueError("MT5 disconnected")
        tick = mt.symbol_info_tick(symbol)
        if not tick or len(history) < 64:
            raise ValueError("Insufficient quote or snapshot history for native bridge")
        tf = mt.TIMEFRAME_M30 if half else mt.TIMEFRAME_H1
        begin = datetime.fromtimestamp(history[-64]["time"],timezone.utc)
        until = datetime.fromtimestamp(tick.time,timezone.utc)
        rates = mt.copy_rates_range(symbol, tf, begin, until)
        if rates is None or not len(rates) or int(rates[-1]["time"]) != tick.time // step * step:
            raise ValueError("Native bridge has no quote-matched current bar")
        native = [dict(time=int(r["time"]), **{k: float(r[k]) for k in ("open","high","low","close")})
                  for r in rates[:-1]]
        bytime = {b["time"]: b for b in native}
        overlap = history[-64:]
        if any(b["time"] not in bytime for b in overlap):
            raise ValueError("Native bridge could not verify the last 64 published bars")
        mismatches = [(b["time"], k, b[k], bytime[b["time"]][k]) for b in overlap
                      for k in ("open","high","low","close") if abs(b[k] - bytime[b["time"]][k]) > 1e-6]
        revision = epoch("2026-11-17 17:00:00")
        expected = [(revision, "close", 111.415, 111.475)]
        if mismatches:
            if symbol != "CADJPY.pro" or mismatches != expected:
                raise ValueError("Unreconciled published/native OHLC on " + symbol)
            result = [b for b in history if b["time"] < revision] + [b for b in native if b["time"] >= revision]
            note = "MT5 corrected 17 Nov close; published CADJPY snapshot held"
        else:
            result = history + [b for b in native if b["time"] > history[-1]["time"]]
            note = "MT5 history joined to 64 verified dashboard candles"
        return hours(result,half), int(tick.time), note
    finally:
        mt.shutdown()


def read_inputs():
    context = market.build()
    assets = [a for a in load(SITE / "assets.json")["assets"] if a.get("status") == "published" and a.get("email_enabled", True)]
    if not assets or len({a["symbol"] for a in assets}) != len(assets):
        raise ValueError("Invalid published asset registry")
    clock_samples = []
    for view in context["assets"].values():
        if view.get("state") == "VERIFIED_NATIVE_CONTEXT":
            delta = view["tick_native"] - datetime.fromisoformat(view["observed_at_utc"]).timestamp()
            offset = round(delta / HOUR) * HOUR
            if abs(offset) <= 14*HOUR and abs(delta - offset) <= 45:
                clock_samples.append(offset)
    if len(clock_samples) < 3:
        # A stalled web publisher can exhaust the shared chart overlay window.
        # Read live broker clocks directly so independent native bridges still work.
        import MetaTrader5 as mt
        if mt.initialize():
            try:
                for asset in assets:
                    tick = mt.symbol_info_tick(asset["symbol"])
                    if tick:
                        delta = tick.time - datetime.now(timezone.utc).timestamp()
                        h = round(delta / HOUR) * HOUR
                        if abs(h) <= 14*HOUR and abs(delta-h) <= 45:
                            clock_samples.append(h)
            finally:
                mt.shutdown()
    if len(clock_samples) < 3:
        # Overnight/holiday: healthy offline bars may still exist, but an uncertain
        # clock cannot advance the live cutover or define a Kampala-day replay.
        raise ValueError("Too few contemporaneous quotes to map broker labels to UTC")
    offset = int(statistics.median(clock_samples))
    if clock_samples.count(offset) <= len(clock_samples) // 2:
        raise ValueError("Broker clock samples disagree")
    return assets, context, offset


def instrument(asset, context):
    symbol = asset["symbol"]
    kind = next(k for k, (_, s) in market.ASSETS.items() if s == symbol)
    view = context["assets"][kind]
    snap = load(SITE / asset["snapshot"])
    history = [bar(b) for b in snap["candles"]]
    note = "Dashboard candles + verified MT5"
    if view.get("state") != "VERIFIED_NATIVE_CONTEXT":
        why = view.get("reason", "")
        if "Insufficient published/source overlap" in why or (kind == "cadjpy" and "OHLC mismatch" in why):
            rows, tick, note = native_bridge(asset, history)
        else:
            raise ValueError(view.get("reason", "Current chart context unavailable"))
    else:
        tick = view["tick_native"]
        half = view["period_seconds"] == 1800
        history = [b for b in history if b["time"] + view["period_seconds"] <= tick]
        base = hours(history, half)
        tail = hours([bar(b) for b in view["completed"]], half)
        if not base or not tail or not any(b["time"] == base[-1]["time"] for b in tail) and base[-1]["time"] < tail[0]["time"]:
            raise ValueError("Chart history and native tail do not overlap")
        rows = base + [b for b in tail if b["time"] > base[-1]["time"]]
    if len(rows) < 251 or rows[-1]["time"] + HOUR > tick:
        raise ValueError("Insufficient confirmed hourly bars")
    if any(a["time"] >= b["time"] for a,b in zip(rows,rows[1:])):
        raise ValueError("Duplicate or out-of-order hourly bars")
    return kind, rows, note


def xaueur_boxes(through):
    from xaueur.build_snapshot import build
    clusters = []
    snapshot = build(cluster_sink=clusters)
    if not snapshot["validation"]["archived_outcomes_exact"] or epoch(snapshot["data_asof"]) < through:
        raise ValueError("XAUEUR model has not validated through the chart cutoff")
    return [dict(at=epoch(c["detected_at"]),model="XAUEUR H1-P1 v2.0",trio=c["trio"],
                 low=c["low"],high=c["high"],ratio=c["width_ATR"])
            for c in clusters if epoch(c["detected_at"]) <= through]


def replay_breakouts(boxes, rows, bounds):
    # Record only in retrospective reports. A close exactly on an edge stays inside.
    start, end = bounds
    bar_ends = [r["time"] + HOUR for r in rows]
    stop = bisect_right(bar_ends, end - 1)
    for at, box in boxes.items():
        if not start <= at < end:
            continue
        box["first_break"] = None
        for i in range(bisect_right(bar_ends, at), stop):
            close = rows[i]["close"]
            if close > box["high"] or close < box["low"]:
                box["first_break"] = dict(side="BUY" if close > box["high"] else "SELL",
                                          at=bar_ends[i], close=close)
                break


def collect(assets, context, replay_bounds=None):
    results, errors = {}, {}
    for asset in assets:
        try:
            kind, rows, note = instrument(asset, context)
            extra = []
            if kind == "gold":
                extra = gold_boxes(rows)
            elif kind == "xaueur":
                extra = xaueur_boxes(rows[-1]["time"] + HOUR)
            watch = {e["at"]: None for e in extra}
            require_cross = kind == "gbpusd"
            events = chart_boxes(rows, watch if not require_cross else None, require_cross) + extra
            combined = {}
            for event in sorted(events, key=lambda e: e["at"]):
                t = event["at"]
                if require_cross:
                    confirm = event.get("confirmation")
                    if confirm is None:
                        continue
                    combined[confirm["at"]] = dict(
                        symbol=asset["symbol"], kind=kind, digits=asset["digits"], source=note,
                        at=confirm["at"], formed_at=t, crossed_at=confirm["crossed_at"],
                        confirmation_close=confirm["close"], low=event["low"], high=event["high"],
                        watch=dict(side=confirm["side"], reason="ema_cross_and_box"),
                        rules=[dict(model=event["model"], trio=event["trio"], ratio=event["ratio"])])
                    continue
                if t not in combined:
                    combined[t] = dict(symbol=asset["symbol"], at=t, low=event["low"], high=event["high"],
                                       digits=asset["digits"], kind=kind, rules=[], source=note,
                                       watch=watch.get(t))
                combined[t]["rules"].append({k:event[k] for k in ("model","trio","ratio")})
            if replay_bounds is not None and not require_cross:
                replay_breakouts(combined, rows, replay_bounds)
            results[asset["symbol"]] = (rows[-1]["time"] + HOUR, combined, note)
        except Exception as exc:
            errors[asset["symbol"]] = str(exc)
    return results, errors
