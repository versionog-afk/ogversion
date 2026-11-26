# Build registered stack + per-pixel resolution weights, weighted median in mock space
from common import *
from reg2 import *
import pickle
def wmap(key,field):
    H=np.array(d[key]['H'])@np.diag([3.0/K,3.0/K,1.0])
    xs,ys=np.meshgrid(np.arange(WW,dtype=np.float32),np.arange(WH,dtype=np.float32))
    xs=xs+field[0].astype(np.float32); ys=ys+field[1].astype(np.float32)
    den=H[2,0]*xs+H[2,1]*ys+H[2,2]
    mx=((H[0,0]*xs+H[0,1]*ys+H[0,2])/den); my=((H[1,0]*xs+H[1,1]*ys+H[1,2])/den)
    a=np.gradient(mx,axis=1); b=np.gradient(mx,axis=0); c=np.gradient(my,axis=1); e=np.gradient(my,axis=0)
    # singular values of [[a,b],[c,e]]
    S1=a*a+b*b+c*c+e*e; S2=np.sqrt(np.maximum((a*a+b*b-c*c-e*e)**2+4*(a*c+b*e)**2,0))
    smin=np.sqrt(np.maximum((S1-S2)/2,0)); smax=np.sqrt((S1+S2)/2)
    return smin.astype(np.float32),smax.astype(np.float32)
def one(key):
    fields=pickle.load(open('fields.pkl','rb'))
    f=(fields[key][0].astype(np.float32),fields[key][1].astype(np.float32))
    img,valid=warp(key,f)
    smin,smax=wmap(key,f)
    return (norm_ink(img)*255).astype(np.uint8),(valid>0),smin.astype(np.float16),smax.astype(np.float16)
def weighted_median(imgs,w):
    """imgs (N,H,W) uint8, w (N,H,W) float32 -> (H,W) float"""
    N,H,Wd=imgs.shape; out=np.zeros((H,Wd),np.float32)
    for y0 in range(0,H,64):
        a=imgs[:,y0:y0+64].astype(np.float32); ww=w[:,y0:y0+64]
        o=np.argsort(a,axis=0)
        sa=np.take_along_axis(a,o,0); sw=np.take_along_axis(ww,o,0)
        cw=np.cumsum(sw,axis=0); tot=cw[-1]
        idx=(cw>=tot[None]*0.5).argmax(0)
        m=np.take_along_axis(sa,idx[None],0)[0]
        out[y0:y0+64]=np.where(tot>0,m,0)
    return out
if __name__=='__main__':
    with Pool(4) as p: res=p.map(one,KEYS)
    imgs=np.array([r[0] for r in res]); vals=np.array([r[1] for r in res]); smin=np.array([r[2] for r in res]); smax=np.array([r[3] for r in res])
    np.save('stack_imgs.npy',imgs); np.save('stack_vals.npy',vals); np.save('stack_smin.npy',smin); np.save('stack_smax.npy',smax)
    w=(smin.astype(np.float32)**2)*vals
    # penalise strong foreshortening
    w*=np.clip(1.6-smax.astype(np.float32)/np.maximum(smin.astype(np.float32),1e-3),0,1)
    med=weighted_median(imgs,w)
    cv2.imwrite('wmed.png',med.astype(np.uint8))
    # frontal-only median (wb + 57..90)
    fi=[i for i,k in enumerate(KEYS) if k=='wb' or int(k)<=90]
    medf=weighted_median(imgs[fi],w[fi]); cv2.imwrite('wmed_frontal.png',medf.astype(np.uint8))
    hi=[i for i,k in enumerate(KEYS) if k!='wb' and int(k)>=99]
    medh=weighted_median(imgs[hi],w[hi]); cv2.imwrite('wmed_hi.png',medh.astype(np.uint8))
    cv2.imwrite('wsum.png',np.clip(w.sum(0)*4,0,255).astype(np.uint8))
    cv2.imwrite('wb_reg.png',imgs[0])
