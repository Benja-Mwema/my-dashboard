import json, sys, threading, http.server, functools

from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'vendor'))
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parent
results=[]
base=sys.argv[1] if len(sys.argv)>1 else None
if base is None:
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(P/'preview')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    for width,height in [(1440,1000),(390,844)]:
        page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'usdjpy.html',wait_until='networkidle')
        page.wait_for_function('window.USDJPYDashboard?.getData()?.entries.length===55')
        assert page.locator('#counts').inner_text()=='55'
        assert page.locator('#order').inner_text() in ['BULLISH','BEARISH','MIXED']
        assert page.locator('#chart svg').count()==1
        assert page.locator('a.aurum-topnav-link[href="usdjpy.html"]').count()==1
        assert page.locator('#instrument').input_value()=='usdjpy.html'
        page.screenshot(path=str(P/f'usdjpy_{width}.png'),full_page=True)
        page.locator('[data-tab="research"]').click()
        assert page.locator('#entries tr').count()==55
        page.select_option('#side','BUY');assert page.locator('#entries tr').count()==34
        page.locator('[data-record]').first.click()
        assert page.locator('#evidencePanel').is_visible()
        assert page.locator('#evidence tr').count()==12
        before=page.locator('#range').inner_text();page.locator('#earlier').click();assert page.locator('#range').inner_text()!=before
        page.locator('[data-tab="audit"]').click()
        assert page.locator('#audit').is_visible() and not page.locator('#chartPanel').is_visible()
        assert 'Frozen: true' in page.locator('#auditText').inner_text()
        page.select_option('#dataset','usdjpy-replay.json');page.wait_for_function("document.getElementById('quality').textContent==='FROZEN_REPLAY'")
        assert not any(b.get('provisional') for b in page.evaluate('window.USDJPYDashboard.getBars()'))
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not errors,errors
        results.append({'width':width,'formations':55,'buy_filter':34,'inspect':True,'pan':True,'audit':True,'replay_excludes_forming':True,'mobile_overflow':False,'javascript_errors':errors})
        page.close()
    if len(sys.argv)>2 and sys.argv[2]=='--all-routes':
        page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        for name in ['index','xaueur','gbpjpy','audcad','ws30','dax40','cadjpy','eurjpy','gbpusd','eurusd','nas100','cac40','jpn225','aus200']:
            page.goto(base+name+'.html',wait_until='domcontentloaded',timeout=60000)
            page.wait_for_selector('a.aurum-topnav-link[href="usdjpy.html"]',timeout=30000)
            page.wait_for_function('window.AurumCharts && AurumCharts.getState().bars>0',timeout=60000)
            assert not errors,(name,errors)
            results.append({'route':name,'chart_loaded':True,'usd_jpy_navigation':True,'javascript_errors':[]})
        page.close()
    browser.close()
(P/('public_ui_acceptance.json' if len(sys.argv)>1 else 'ui_acceptance.json')).write_text(json.dumps(results,indent=2))
print(json.dumps(results))
