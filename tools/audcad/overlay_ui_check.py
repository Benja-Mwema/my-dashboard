import sys,json
from pathlib import Path
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'vendor'))
from playwright.sync_api import sync_playwright
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8124';errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe');page=b.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base+'/audcad.html');page.wait_for_selector('#entries tr');page.select_option('#dataset','audcad-replay.json');page.wait_for_function("document.querySelector('#quality').textContent==='Frozen replay'")
 assert page.locator('#exitMode').input_value()=='overlay'
 ids=page.evaluate("data.entries.filter(e=>e.exit_overlay.status==='TP60').map(e=>e.id)");assert ids;page.select_option('#selected',ids[0]);assert page.locator('[data-role="target-guide"]').count()==1;assert page.locator('[data-role="post-tp"]').count()>0;assert 'excluded from trade P/L' in page.locator('#overlayCaption').inner_text();page.screenshot(path=str(r/'overlay_desktop.png'),full_page=True)
 ids=page.evaluate("data.entries.filter(e=>e.direction==='BUY'&&e.exit_overlay.status==='BE').map(e=>e.id)");assert ids;page.select_option('#selected',ids[0]);assert page.locator('[data-role="reversal"]').count()>0;assert 'Overlay BE' in page.locator('#detail').inner_text();assert page.locator('[data-role="post-tp"]').count()==0
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(r/'overlay_mobile.png'),full_page=True)
 page.select_option('#exitMode','frozen');assert page.locator('#gross').inner_text()=='180.0';assert page.locator('#rate').inner_text()=='52.6%';page.select_option('#side','SELL');assert page.locator('#gross').inner_text()=='0.0';assert page.locator('#rate').inner_text()=='50.0%';assert not errors,errors;b.close()
print('PASS: target dots, observed solid, reversal spaced dots, BE termination, purple post-TP, mobile and frozen parity')
