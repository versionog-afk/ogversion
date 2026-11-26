import numpy as np,sys
F=int(sys.argv[1]) if len(sys.argv)>1 else 961
res=np.load('dbg/notepairs_%d.npy'%F,allow_pickle=True)
good=[r for r in res if r['n']>=30 and r['area']>8000]
print(len(good),'pairs')
def ratio(A,d,sh=0.0):
    D=np.array([[1,sh],[0,d]]); B=np.linalg.inv(D)@A@D; s=np.linalg.svd(B,compute_uv=False); return s[0]/s[1]
ds=np.linspace(0.85,1.25,401)
tot=np.zeros_like(ds)
for r in good:
    rr=np.array([ratio(r['A'],d) for d in ds]); i=rr.argmin()
    # bootstrap spread of best d
    bd=[ds[np.argmin([ratio(Mb,d) for d in ds[::4]])*4] for Mb in r['Ms'][:60]]
    sens=np.sin(np.radians(r['rot']))**2
    print('%-22s n %3d rot %7.1f det %.3f  ratio@d=1 %.3f  best d %.3f (boot %.3f..%.3f) min ratio %.3f  sens %.2f'%(r['name'],r['n'],r['rot'],np.linalg.det(r['A']),ratio(r['A'],1.0),ds[i],np.percentile(bd,10),np.percentile(bd,90),rr[i],sens))
    tot+=np.log(rr)**2
print('consensus d (sum log^2 ratio):',ds[tot.argmin()])
# 2-parameter: d and shear
best=None
for d in np.linspace(0.9,1.2,61):
    for sh in np.linspace(-0.1,0.1,41):
        c=sum(np.log(ratio(r['A'],d,sh))**2 for r in good)
        if best is None or c<best[0]: best=(c,d,sh)
print('consensus d, shear:',best)
