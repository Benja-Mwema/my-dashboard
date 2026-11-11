import sys
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parent/'vendor'))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe');page=b.new_page();page.goto('http://127.0.0.1:8124/gbpjpy.html');page.wait_for_selector('#entries tr');page.route('**/gbpjpy-data.json*',lambda r:r.fulfill(status=503,body='unavailable'));page.select_option('#dataset','gbpjpy-data.json');page.wait_for_function("document.querySelector('#sourceStatus').textContent==='Snapshot unavailable'");assert page.locator('#count').inner_text()=='—';assert page.locator('#entries tr').count()==0;assert page.locator('#directionArrow').is_hidden();b.close()
print('PASS: failed snapshot clears old metrics, signals and direction')
