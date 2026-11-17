'use strict';
/* AURUM Unified Dashboard Shell v1.0 — presentation only.
   Shared navigation. Deliberately does not read price JSON, indicators,
   outcomes, reference prices, market timestamps or change model decisions. */
(function(){
  const here=location.pathname.toLowerCase();
  const selected=here.endsWith('/cadjpy.html')?'cadjpy':here.endsWith('/gbpjpy.html')?'gbpjpy'
    :here.endsWith('/audcad.html')?'audcad'
    :here.endsWith('/ws30.html')?'ws30'
    :here.endsWith('/dax40.html')?'dax40'
    :(new URLSearchParams(location.search).get('asset')||'XAUUSD.pro')==='XAUUSD.pro'?'gold':'';
  const routes=[
    {id:'cadjpy',label:'CADJPY',symbol:'CADJPY.pro',href:'cadjpy.html'},
    {id:'gold',label:'Gold',symbol:'XAUUSD.pro',href:'index.html?asset=XAUUSD.pro'},
    {id:'gbpjpy',label:'GBPJPY',symbol:'GBPJPY.pro',href:'gbpjpy.html'},
    {id:'audcad',label:'AUDCAD',symbol:'AUDCAD.pro',href:'audcad.html'},
    {id:'ws30',label:'WS30',symbol:'WS30.pro',href:'ws30.html'},
    {id:'dax40',label:'DAX40',symbol:'DAX40.pro',href:'dax40.html'}
  ];
  const mount=()=>{
    const header=document.querySelector('body.aurum-ui-v1 > header');
    if(!header || document.querySelector('.aurum-topnav'))return;
    const nav=document.createElement('nav');
    nav.className='aurum-topnav';
    nav.setAttribute('aria-label','AURUM published instrument dashboards');
    const inner=document.createElement('div');
    inner.className='aurum-topnav-inner';
    const title=document.createElement('span');
    title.className='aurum-topnav-title';
    title.textContent='Published research';
    inner.append(title);
    const links=document.createElement('div');
    links.className='aurum-topnav-links';
    for(const route of routes){
      const a=document.createElement('a');
      a.className='aurum-topnav-link';
      a.href=route.href;
      a.textContent=route.label;
      a.dataset.asset=route.symbol;
      a.title=route.symbol+' — research module';
      if(route.id===selected){a.setAttribute('aria-current','page');a.title+=' — current page';}
      links.append(a);
    }
    inner.append(links);
    const suffix=document.createElement('span');
    suffix.className='aurum-topnav-suffix';
    suffix.textContent='Research signals · not executed trades';
    inner.append(suffix);
    nav.append(inner);
    header.insertAdjacentElement('afterend',nav);
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});
  else mount();
})();
