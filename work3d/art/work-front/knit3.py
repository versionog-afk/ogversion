import numpy as np
from lm import lm
W=np.load('dbg/knitW.npy'); C=np.load('dbg/knitC.npy')
def grad3(p,x,y,gh):
    a,b,c0=p; gg,hh=gh
    d=gg*x+hh*y+1; n=a*x+b*y+c0
    return (a*d-n*gg)/d**2,(b*d-n*hh)/d**2
def mk(Wd,Cd):
    def res(q):
        gh=q[:2]; out=[]
        if len(Wd):
            gx,gy=grad3(q[2:5],Wd[:,0],Wd[:,1],gh); nw=np.hypot(Wd[:,2],Wd[:,3]); out+=[(gx-Wd[:,2])/nw,(gy-Wd[:,3])/nw]
        if len(Cd):
            hx,hy=grad3(q[5:8],Cd[:,0],Cd[:,1],gh); nc=np.hypot(Cd[:,2],Cd[:,3]); out+=[(hx-Cd[:,2])/nc,(hy-Cd[:,3])/nc]
        return np.concatenate(out)
    return res
q0=np.array([0,1/3530.,1/15.,0,0,0,1/9.,0]); sc=[1e-5,1e-5,1e-3,1e-3,1,1e-3,1e-3,1]
q,rr=lm(mk(W,C),q0,scale=sc,robust=0.03)
# reject outliers and refit (2 rounds)
for rnd in range(3):
    gx,gy=grad3(q[2:5],W[:,0],W[:,1],q[:2]); nw=np.hypot(W[:,2],W[:,3]); ew=np.hypot(gx-W[:,2],gy-W[:,3])/nw
    hx,hy=grad3(q[5:8],C[:,0],C[:,1],q[:2]); nc=np.hypot(C[:,2],C[:,3]); ec=np.hypot(hx-C[:,2],hy-C[:,3])/nc
    kw=ew<0.05; kc=ec<0.06
    q,rr=lm(mk(W[kw],C[kc]),q,scale=sc,robust=0.02)
    print('round',rnd,'kept',kw.sum(),'/',len(W),kc.sum(),'/',len(C),'rms',np.sqrt(np.mean(rr**2)),'VL y@960',-(1+q[0]*960)/q[1],'slope',-q[0]/q[1])
np.save('dbg/knitfit.npy',q); np.save('dbg/knit_keep.npy',np.array([kw.sum(),kc.sum()]))
# stability: wales only / courses only / halves
qa,_=lm(mk(W[kw],C[:0]),q,scale=sc,robust=0.02); print('wales only VL y@960',-(1+qa[0]*960)/qa[1],'slope',-qa[0]/qa[1])
qb,_=lm(mk(W[:0],C[kc]),q,scale=sc,robust=0.02); print('courses only VL y@960',-(1+qb[0]*960)/qb[1],'slope',-qb[0]/qb[1])
for name,sel in (('top',lambda D:D[:,1]<1280),('bottom',lambda D:D[:,1]>=1000),('left',lambda D:D[:,0]<960),('right',lambda D:D[:,0]>=960)):
    Wd=W[kw]; Cd=C[kc]
    qc,_=lm(mk(Wd[sel(Wd)],Cd[sel(Cd)]),q,scale=sc,robust=0.02); print(name,'VL y@960',-(1+qc[0]*960)/qc[1],'slope',-qc[0]/qc[1], len(Wd[sel(Wd)]),len(Cd[sel(Cd)]))
# residual map (signed, along-gradient) per region
Wd=W[kw]; gx,gy=grad3(q[2:5],Wd[:,0],Wd[:,1],q[:2]); 
rel=(np.hypot(gx,gy)-np.hypot(Wd[:,2],Wd[:,3]))/np.hypot(Wd[:,2],Wd[:,3])
dang=np.degrees(np.arctan2(gy,gx)-np.arctan2(Wd[:,3],Wd[:,2]))
for y0 in range(0,2560,320):
    row=[]
    for x0 in range(0,1920,320):
        s=(Wd[:,0]>=x0)&(Wd[:,0]<x0+320)&(Wd[:,1]>=y0)&(Wd[:,1]<y0+320)
        row.append('%+5.1f%%/%+4.1f°(%2d)'%(100*rel[s].mean(),dang[s].mean(),s.sum()) if s.sum() else '      --       ')
    print(y0,' '.join(row))
