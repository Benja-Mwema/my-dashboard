"""Build Render's static publish directory from the current snapshot checkout."""
import hashlib
import json
import re
import shutil
import subprocess
from html import escape
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist"
TEMPLATES = ROOT / "tools" / "delivery"


def write_json(path, data):
    path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf-8")


def payload(directory, key, kind, data):
    raw = json.dumps(data, separators=(",", ":"), allow_nan=False).encode()
    path = f"{key}-{kind}-{hashlib.sha256(raw).hexdigest()[:24]}.json"
    (directory / path).write_bytes(raw)
    return path


def main():
    # Render starts from a checkout. Empty only our own previous generated output.
    if OUTPUT.exists():
        if not (OUTPUT / ".aurum-delivery-build").is_file():
            raise RuntimeError("dist already exists and was not created by this builder")
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()
    (OUTPUT / ".aurum-delivery-build").touch()
    # Publish only repository files. Local credentials and build output must stay outside dist.
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, files):
        if name.startswith(".") or name.startswith("tools/delivery/") or name == "tools/build_delivery.py":
            continue
        destination = OUTPUT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    data_dir = OUTPUT / "delivery"
    history = OUTPUT / "history"
    data_dir.mkdir()
    history.mkdir()
    for name in ("recent.js", "recent.css", "delivery.js"):
        shutil.copyfile(TEMPLATES / name, OUTPUT / name)
    context = json.loads((ROOT / "market-context.json").read_bytes())
    if context["version"] != "AURUM_MARKET_CONTEXT_1":
        raise ValueError("Unknown chart context format")
    registry = json.loads((ROOT / "assets.json").read_bytes())
    assets = [a for a in registry["assets"] if a["status"] == "published"]
    pages = {a["symbol"]: a.get("module_page") or "index.html" for a in assets}
    template = Template((TEMPLATES / "recent.html").read_text())
    for asset in assets:
        symbol = asset["symbol"]
        key = "gold" if symbol == registry["default_symbol"] else symbol.split(".")[0].lower()
        source = context["assets"].get(key, {"symbol": symbol, "state": "UNAVAILABLE",
                                             "reason": "Instrument missing from chart context"})
        if source["symbol"] != symbol:
            raise ValueError(f"Context identity mismatch for {symbol}")
        # Keep times and broker prices exactly as published. Only closed bars enter the preview.
        recent = {"symbol": symbol, "timeframe": source.get("timeframe", asset["timeframe"]),
                  "state": source["state"], "reason": source.get("reason"),
                  "source_warning": source.get("source_warning"), "candles": source.get("completed", [])[-96:]}
        revision = {"recent": payload(data_dir, key, "recent", recent),
                    "context": payload(data_dir, key, "context", source),
                    "observed": source.get("observed_at_utc")}
        write_json(data_dir / f"{key}.json", revision)
        page = pages[symbol]
        original = (ROOT / page).read_text(encoding="utf-8")
        # A base URL keeps existing scripts, downloads and dataset links at their original paths.
        original = re.sub(r"<head(\s[^>]*)?>", lambda m: m[0] + '<base href="../"><script src="delivery.js" defer></script>', original, count=1, flags=re.I)
        (history / page).write_text(original, encoding="utf-8")
        options = "".join(f'<option value="{escape(pages[a["symbol"]])}" data-symbol="{escape(a["symbol"])}"'
                          + (" selected" if a == asset else "")
                          + f'>{escape(a["symbol"])}</option>' for a in assets)
        (OUTPUT / page).write_text(template.substitute(
            symbol=escape(symbol), key=escape(key), label=escape(asset["model_label"]),
            history=escape("history/" + page), options=options), encoding="utf-8")
    print(f"Built {len(assets)} recent charts and full dashboards in dist")


if __name__ == "__main__":
    main()
