# Stage 1: homography  mock*Ks -> source image px, by ECC on blurred ink, init from largest-CC bbox
from common import *
import json, sys
from multiprocessing import Pool
Ks=3
r=mock_ref()
ref=cv2.resize(r,None,fx=Ks,fy=Ks,interpolation=cv2.INTER_CUBIC)
ref[:40*Ks,:]=0      # remove the caption (above the map in the mockup)
mb=(10,46,218,207)   # mock largest-cc bbox
def ink_of_gray(g):
    dark=(g<75).astype(np.uint8)
    cl=cv2.morphologyEx(dark,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(41,41)))
    n,lab,st,cen=cv2.connectedComponentsWithStats(cl)
    k=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); shirt=(lab==k).astype(np.uint8)
    shirt=cv2.erode(shirt,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15)))
    ink=((g>125)&(shirt>0)).astype(np.uint8)
    n,lab,st,cen=cv2.connectedComponentsWithStats(ink,connectivity=8)
    k=1+np.argmax(st[1:,cv2.CC_STAT_AREA])
    return shirt,ink,tuple(int(v) for v in st[k,:4])
def load(key):
    if key=='wb':
        im=cv2.imread(SRC+'worn-back.png')[700:1500,250:1000]   # offset (250,700)
        return cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32),(250,700)
    return cv2.cvtColor(frame(int(key)),cv2.COLOR_BGR2GRAY).astype(np.float32),(0,0)
def reg(key):
    g,off=load(key)
    shirt,ink,bb=ink_of_gray(g)
    x,y,w,h=bb; Hh,Ww=g.shape
    f=np.clip((g-60)/140,0,1)*(shirt>0)
    msk=np.zeros_like(f); x0=max(0,x-int(.12*w)); x1=min(Ww,x+w+int(.12*w)); y0=max(0,y-int(.08*h)); y1=min(Hh,y+h+int(.02*h))
    msk[y0:y1,x0:x1]=1; f=f*msk
    sx=w/(mb[2]*Ks); sy=h/(mb[3]*Ks)
    H=np.array([[sx,0,x-sx*mb[0]*Ks],[0,sy,y-sy*mb[1]*Ks],[0,0,1]],np.float32)
    ok=True; cc=-1
    try:
        for sig,mode,iters in [(9,cv2.MOTION_AFFINE,200),(5,cv2.MOTION_HOMOGRAPHY,300),(3,cv2.MOTION_HOMOGRAPHY,300)]:
            fb=cv2.GaussianBlur(f,(0,0),sig*sx)
            rb=cv2.GaussianBlur(ref,(0,0),sig)
            crit=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,iters,1e-7)
            if mode==cv2.MOTION_AFFINE:
                cc,A=cv2.findTransformECC(rb,fb,H[:2].copy(),mode,crit,None,1); H[:2]=A
            else:
                cc,H=cv2.findTransformECC(rb,fb,H.copy(),mode,crit,None,1)
    except cv2.error as e:
        ok=False
    if ok:
        wr=cv2.warpPerspective(f,H,(ref.shape[1],ref.shape[0]),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP)
        ov=np.zeros(ref.shape+(3,),np.float32); ov[...,2]=ref; ov[...,1]=wr; ov[...,0]=wr
        os.makedirs('reg1',exist_ok=True)
        cv2.imwrite('reg1/%s.jpg'%key,(np.clip(ov,0,1)*255).astype(np.uint8))
    # H maps mock*Ks px -> cropped-source px ; add crop offset so it maps to full source px
    T=np.array([[1,0,off[0]],[0,1,off[1]],[0,0,1]],np.float64)
    Hf=T@H.astype(np.float64)
    return key,{'H':Hf.tolist(),'cc':float(cc),'ok':ok,'bbox':[bb[0]+off[0],bb[1]+off[1],bb[2],bb[3]]}
if __name__=='__main__':
    keys=['wb']+[str(i) for i in range(57,146)]
    with Pool(4) as p: res=p.map(reg,keys)
    json.dump(dict(res),open('reg1.json','w'))
    for k,v in res: print(k,v['ok'],'%.4f'%v['cc'])
