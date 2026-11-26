# Stage 3: re-register every frame against the registered still photo (wb), then groupwise against the
# resolution-weighted median.
from common import *
import reg2
from reg2 import *
from stack import wmap, weighted_median
import pickle
def work3(args):
    key,field,params=args
    img,valid=warp(key,field)
    I=norm_ink(img)
    step,patch,search,sig,sn,cthr=params
    U,Vv,C=block_match(reg2.TEMPLATE,I,valid,step,patch,search,sig)
    fu,fv,frac=smooth_field(U,Vv,C,step,sn,cthr)
    nf=compose(field,fu,fv)
    return key,nf,float(np.sqrt((fu**2+fv**2).mean())),frac
def one(args):
    key,f=args
    img,valid=warp(key,f)
    if f is None: f=(np.zeros((WH,WW),np.float32),)*2
    smin,smax=wmap(key,f)
    w=(smin**2)*valid*np.clip(1.6-smax/np.maximum(smin,1e-3),0,1)
    return (norm_ink(img)*255).astype(np.uint8),w.astype(np.float16)
def wmedian(keys,fields,pool):
    res=pool.map(one,[(k,fields[k]) for k in keys])
    imgs=np.array([r[0] for r in res]); w=np.array([r[1] for r in res]).astype(np.float32)
    return weighted_median(imgs,w)/255.0,imgs,w
if __name__=='__main__':
    old=pickle.load(open('fields.pkl','rb'))
    fields={k:None for k in KEYS}
    fields['wb']=(old['wb'][0].astype(np.float32),old['wb'][1].astype(np.float32))
    img,valid=warp('wb',fields['wb']); Twb=norm_ink(img)
    others=[k for k in KEYS if k!='wb']
    rounds=[('wb',(96,352,110,7,2.0,0.3)),('wb',(64,224,40,4,2.2,0.35)),('wb',(48,160,20,3,1.8,0.4)),('wb',(40,128,12,2.5,1.6,0.45)),
            ('med',(32,96,10,2,1.5,0.5)),('med',(24,80,8,1.5,1.5,0.5)),('med',(24,72,6,1.2,1.3,0.5)),('med',(20,64,5,1.0,1.3,0.5))]
    for ri,(tname,params) in enumerate(rounds):
        if tname=='wb': T=Twb; keys=others
        else:
            with Pool(4) as p: T,_,_=wmedian(KEYS,fields,p)
            T=T.astype(np.float32); cv2.imwrite('med3_round%d.png'%ri,(T*255).astype(np.uint8)); keys=KEYS
        with Pool(4,initializer=init_pool,initargs=(T,)) as p:
            res=p.map(work3,[(k,fields[k],params) for k in keys])
        for k,nf,rms,frac in res: fields[k]=nf
        print('round',ri,tname,params,'rms update: mean %.2f max %.2f'%(np.mean([r[2] for r in res]),np.max([r[2] for r in res])),' frac %.2f'%np.mean([r[3] for r in res]),flush=True)
    pickle.dump({k:(v[0].astype(np.float16),v[1].astype(np.float16)) for k,v in fields.items()},open('fields3.pkl','wb'))
    with Pool(4) as p: T,imgs,w=wmedian(KEYS,fields,p)
    cv2.imwrite('wmed3.png',(T*255).astype(np.uint8))
    np.save('stack3_imgs.npy',imgs); np.save('stack3_w.npy',w.astype(np.float16))
    cv2.imwrite('wsum3.png',np.clip(w.sum(0)*4,0,255).astype(np.uint8))
