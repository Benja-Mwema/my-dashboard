from pathlib import Path
import sys,threading,http.server,functools,json
P=Path(__file__).parent;sys.path.insert(0,str(P.parent/'vendor'))
from playwright.sync_api import sync_playwright
s=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(P/'preview')));threading.Thread(target=s.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe');page=b.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{s.server_port}/gbpusd.html');page.wait_for_function('window.AurumCharts && AurumCharts.getState().forming');page.screenshot(path=str(P/'top.png'));page.locator('#acPlot').scroll_into_view_if_needed();page.screenshot(path=str(P/'chart_desktop.png'));page.set_viewport_size({'width':390,'height':844});page.locator('#acPlot').scroll_into_view_if_needed();page.screenshot(path=str(P/'chart_mobile.png'));print(json.dumps(page.evaluate('AurumCharts.getState()')));b.close()