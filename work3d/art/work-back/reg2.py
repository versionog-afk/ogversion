# Stage 2: non-rigid refinement in mock space (work scale K). Groupwise: first to mockup, then to running median.
from common import *
import json, sys, pickle
from multiprocessing import Pool
WW,WH=MW*K,MH*K
d=json.load(open('reg1.json'))
KEYS=['wb']+[str(i) for i in range(57,143)]
def src_gray(key):
    if key=='wb': im=cv2.imread(SRC+'worn-back.png')
    else: im=frame(int(key))
    return cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
def base_maps(key):
    """maps work px -> source px via homography"""
    H=np.array(d[key]['H'])@np.diag([3.0/K,3.0/K,1.0])   # work -> source
    xs,ys=np.meshgrid(np.arange(WW,dtype=np.float32),np.arange(WH,dtype=np.float32))
    den=H[2,0]*xs+H[2,1]*ys+H[2,2]
    mx=(H[0,0]*xs+H[0,1]*ys+H[0,2])/den; my=(H[1,0]*xs+H[1,1]*ys+H[1,2])/den
    return mx.astype(np.float32),my.astype(np.float32)
def warp(key,field=None):
    """returns warped gray (0..255 float) in work space and valid mask. field=(fx,fy) displacement in work px (work-> work) applied before homography"""
    g=src_gray(key)
    H=np.array(d[key]['H'])@np.diag([3.0/K,3.0/K,1.0])
    xs,ys=np.meshgrid(np.arange(WW,dtype=np.float32),np.arange(WH,dtype=np.float32))
    if field is not None:
        xs=xs+field[0]; ys=ys+field[1]
    den=H[2,0]*xs+H[2,1]*ys+H[2,2]
    mx=((H[0,0]*xs+H[0,1]*ys+H[0,2])/den).astype(np.float32); my=((H[1,0]*xs+H[1,1]*ys+H[1,2])/den).astype(np.float32)
    out=cv2.remap(g,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    valid=((mx>2)&(my>2)&(mx<g.shape[1]-3)&(my<g.shape[0]-3)).astype(np.float32)
    return out,valid
def norm_ink(img):
    return np.clip((img-55)/150,0,1).astype(np.float32)
def block_match(T,I,valid,step,patch,search,sig=0):
    """for grid nodes, find displacement (u,v) such that I(x+u,y+v) ~ T(x,y). returns grid arrays"""
    if sig>0:
        T=cv2.GaussianBlur(T,(0,0),sig); I=cv2.GaussianBlur(I,(0,0),sig)
    gx=np.arange(step//2,WW,step); gy=np.arange(step//2,WH,step)
    U=np.zeros((len(gy),len(gx)),np.float32); V=np.zeros_like(U); C=np.zeros_like(U)
    h=patch//2
    Ip=cv2.copyMakeBorder(I,h+search,h+search,h+search,h+search,cv2.BORDER_CONSTANT,value=0)
    Tp=cv2.copyMakeBorder(T,h,h,h,h,cv2.BORDER_CONSTANT,value=0)
    Vp=cv2.copyMakeBorder(valid,h,h,h,h,cv2.BORDER_CONSTANT,value=0)
    for j,y in enumerate(gy):
        for i,x in enumerate(gx):
            t=Tp[y:y+patch,x:x+patch]
            if t.std()<0.06 or Vp[y:y+patch,x:x+patch].mean()<0.9: continue
            s=Ip[y:y+patch+2*search,x:x+patch+2*search]
            if s.std()<0.03: continue
            r=cv2.matchTemplate(s,t,cv2.TM_CCOEFF_NORMED)
            _,mxv,_,loc=cv2.minMaxLoc(r)
            px,py=loc
            dx=dy=0.0
            if 0<px<r.shape[1]-1 and 0<py<r.shape[0]-1:
                a,b,c=r[py,px-1],r[py,px],r[py,px+1]; den=a-2*b+c
                if den<0: dx=0.5*(a-c)/den
                a,b,c=r[py-1,px],r[py,px],r[py+1,px]; den=a-2*b+c
                if den<0: dy=0.5*(a-c)/den
            else:
                mxv*=0.3
            U[j,i]=px+dx-search; V[j,i]=py+dy-search; C[j,i]=max(mxv,0)
    return U,V,C
def smooth_field(U,V,C,step,sigma_nodes,cthr=0.5):
    """robust normalized convolution -> dense field (WH,WW)"""
    C=np.where(C>cthr,C,0).astype(np.float32)
    # outlier rejection vs local weighted median-ish (use normalized conv then reject far ones, twice)
    for it in range(2):
        w=cv2.GaussianBlur(C,(0,0),sigma_nodes)+1e-6
        us=cv2.GaussianBlur(U*C,(0,0),sigma_nodes)/w; vs=cv2.GaussianBlur(V*C,(0,0),sigma_nodes)/w
        res=np.hypot(U-us,V-vs)
        thr=max(1.0,2.5*np.median(res[C>0])) if (C>0).any() else 1
        C=np.where(res>thr,0,C)
    w=cv2.GaussianBlur(C,(0,0),sigma_nodes)+1e-6
    us=cv2.GaussianBlur(U*C,(0,0),sigma_nodes)/w; vs=cv2.GaussianBlur(V*C,(0,0),sigma_nodes)/w
    # where no support at all, fields decay to whatever normalized conv gives (extrapolation)
    # upsample to dense
    gx=np.arange(step//2,WW,step); gy=np.arange(step//2,WH,step)
    # build affine from node index to pixel: x = step/2 + i*step
    M=np.array([[step,0,step/2.0],[0,step,step/2.0]],np.float32)
    fu=cv2.warpAffine(us,M,(WW,WH),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    fv=cv2.warpAffine(vs,M,(WW,WH),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    return fu,fv,(C>0).mean()
def compose(field,fu,fv):
    """new field: x -> x + fu(x) then old field applied at that point: total(x)= fu(x) + old(x+fu(x))"""
    if field is None: return fu,fv
    xs,ys=np.meshgrid(np.arange(WW,dtype=np.float32),np.arange(WH,dtype=np.float32))
    ox=cv2.remap(field[0],xs+fu,ys+fv,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    oy=cv2.remap(field[1],xs+fu,ys+fv,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    return fu+ox,fv+oy
SCHED=None
TEMPLATE=None
def work(args):
    key,field,params=args
    img,valid=warp(key,field)
    I=norm_ink(img)
    step,patch,search,sig,sn,cthr=params
    U,Vv,C=block_match(TEMPLATE,I,valid,step,patch,search,sig)
    fu,fv,frac=smooth_field(U,Vv,C,step,sn,cthr)
    nf=compose(field,fu,fv)
    return key,nf,float(np.sqrt((fu**2+fv**2).mean())),frac
def init_pool(T):
    global TEMPLATE; TEMPLATE=T
def stack(keys,fields):
    imgs=[];vals=[]
    for k in keys:
        img,valid=warp(k,fields.get(k)); imgs.append(norm_ink(img)); vals.append(valid)
    return np.array(imgs),np.array(vals)
def masked_median(imgs,vals):
    a=np.where(vals>0,imgs,np.nan)
    with np.errstate(all='ignore'):
        m=np.nanmedian(a,axis=0)
    return np.nan_to_num(m).astype(np.float32)
if __name__=='__main__':
    r=mock_ref(); ref=cv2.resize(r,(WW,WH),interpolation=cv2.INTER_CUBIC); ref[:40*K,:]=0
    ref=np.clip(ref,0,1).astype(np.float32)
    fields={k:None for k in KEYS}
    # (step, patch, search, blur sigma, smoothing sigma in nodes, conf thr)
    rounds=[('mock',(96,352,110,8,2.0,0.3)),('mock',(64,224,40,5,2.5,0.35)),('mock',(48,160,20,4,2.0,0.4)),
            ('med',(40,128,14,2.5,1.6,0.45)),('med',(32,96,10,2,1.5,0.5)),('med',(24,80,8,1.5,1.5,0.5)),('med',(24,72,6,1.2,1.3,0.5))]
    T=ref
    for ri,(tname,params) in enumerate(rounds):
        if tname=='med':
            hi=[k for k in KEYS if k=='wb' or int(k)>=99]
            imgs,vals=stack(hi,fields); T=masked_median(imgs,vals); del imgs,vals
            cv2.imwrite('med_round%d.png'%ri,(T*255).astype(np.uint8))
        with Pool(4,initializer=init_pool,initargs=(T,)) as p:
            res=p.map(work,[(k,fields[k],params) for k in KEYS])
        for k,nf,rms,frac in res:
            fields[k]=nf
        print('round',ri,tname,params,'rms update: mean %.2f max %.2f'%(np.mean([r[2] for r in res]),np.max([r[2] for r in res])),' frac %.2f'%np.mean([r[3] for r in res]),flush=True)
    pickle.dump({k:(v[0].astype(np.float16),v[1].astype(np.float16)) for k,v in fields.items()},open('fields.pkl','wb'))
