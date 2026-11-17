import pandas as pd, numpy as np
def scan(raw):
 f=raw.copy(); f['date']=pd.to_datetime(f.time,unit='s')
 for n in (10,20,50): f[f'e{n}']=f.close.ewm(span=n,adjust=False).mean()
 tr=pd.concat([f.high-f.low,(f.high-f.close.shift()).abs(),(f.low-f.close.shift()).abs()],axis=1).max(axis=1)
 f['atr']=tr.ewm(alpha=1/14,adjust=False).mean()
 f['width']=f[['e10','e20','e50']].max(axis=1)-f[['e10','e20','e50']].min(axis=1)
 f['depth']=f.width/f.atr; f['cl']=(f.close-f.low)/(f.high-f.low)
 for n in (10,20,50): f[f's{n}']=(f[f'e{n}']-f[f'e{n}'].shift(3))/(3*f.atr)
 f['down']=(f.close<f.close.shift()).rolling(3).sum(); f['up']=(f.close>f.close.shift()).rolling(3).sum()
 f['lower']=((f.high<f.high.shift())&(f.low<f.low.shift())).rolling(3).sum()
 f['contig4']=f.time.diff().eq(3600).rolling(3).sum().eq(3)
 records=[]; audit=[]; active=False; used=False; N=0; ep=0; md=np.nan
 for i,r in f.iterrows():
  gap=i==0 or r.time-f.time.iloc[i-1]!=3600
  if gap: active=False
  q=r.depth<=.5
  if q:
   if not active: ep+=1; N=1; used=False; md=r.depth; active=True
   else: N+=1; md=min(md,r.depth)
  eligible=active and not used
  shared=eligible and r.contig4 and r.atr>0 and r.high>r.low and i>0 and r.width>f.width.iloc[i-1]
  sell=shared and 4<=N<=16 and r.e10<r.e20<r.e50 and r.s10<0 and r.s20<0 and r.s50<=0 and r.close<r.e10 and r.close<r.open and r.cl<=.5 and r.down>=2 and r.lower>=2
  buy=shared and 2<=N<=8 and r.e10>r.e20>r.e50 and r.s10>0 and r.s20>0 and r.s50>=0 and r.close>r.e10 and r.close>r.open and r.cl>=.5 and r.up>=2
  if sell or buy:
   rec=r.to_dict(); rec.update(i=i,episode=ep,N=N,min_depth=md,side='SELL' if sell else 'BUY',phase='inside' if q else 'first_outside',decision=r.date+pd.Timedelta(hours=1))
   records.append(rec); used=True
  if r.date.year==2026 and active:
   audit.append(dict(i=i,date=r.date,episode=ep,N=N,min_depth=md,depth=r.depth,phase='inside' if q else 'first_outside',eligible=eligible,shared=shared,sell=sell,buy=buy))
  if not q: active=False
 return f,pd.DataFrame(records),pd.DataFrame(audit)
