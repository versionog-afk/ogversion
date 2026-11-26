# Stage 1 of the matte: automatic silhouette of the printed notes (source pixel grid).
#   strong ink  = clearly bright or clearly coloured
#   weak ink    = dim but still coloured (notes lying in the collage's own shadows) -> kept only where it touches strong ink
#   the grey shadow rim and the cloth are neutral and dim -> outside
# Interior dark areas are kept by hole filling; only the A counter stays open.
import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
def features():
    im=cv2.imread(SRC)
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
    L=lab[...,0]; a=lab[...,1]-128; b=lab[...,2]-128
    # chroma measured from the local cloth/rim neutral point (slightly warm): a0=0, b0=2.2
    ab=np.dstack([cv2.GaussianBlur(a,(0,0),3.0),cv2.GaussianBlur(b-2.2,(0,0),3.0)])
    C=np.hypot(ab[...,0],ab[...,1])
    Lb=cv2.GaussianBlur(L,(0,0),2.5)
    return im,L,Lb,C
def auto_mask(Lb,C,tL=140,tC=16,wL=128,wC=10.5,wLmin=46):
    roi=np.zeros(Lb.shape,np.uint8); roi[585:1715,140:1800]=1
    strong=(((Lb>tL)|((C>tC)&(Lb>50)))&(roi>0)).astype(np.uint8)
    weak=((((C>wC)&(Lb>wLmin))&(roi>0))|(strong>0)).astype(np.uint8)
    # main strong component
    n,l,s,_=cv2.connectedComponentsWithStats(strong,8); main=(l==(np.argmax(s[1:,4])+1)).astype(np.uint8)
    # hysteresis: weak pixels connected to main, but only within 14 px of strong ink (keeps it from creeping along the rim)
    near=cv2.dilate(main,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(29,29)))
    n,l,s,_=cv2.connectedComponentsWithStats((weak&near).astype(np.uint8),8)
    ids=np.unique(l[main>0]); m=np.isin(l,ids[ids>0]).astype(np.uint8)
    return m,strong,weak
def tidy(m,close_r=2,open_r=2):
    k=lambda r:cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,k(close_r))
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,k(open_r))
    n,l,s,_=cv2.connectedComponentsWithStats(m,8); m=(l==(np.argmax(s[1:,4])+1)).astype(np.uint8)
    return m
def fill(m,open_pts=((990,1075),)):
    inv=1-m; n2,l2,s2,_=cv2.connectedComponentsWithStats(inv,4)
    keep={l2[0,0]}|{l2[y,x] for x,y in open_pts}
    return np.where(np.isin(l2,list(keep)),0,1).astype(np.uint8)
if __name__=='__main__':
    im,L,Lb,C=features()
    m,strong,weak=auto_mask(Lb,C)
    m=fill(tidy(m))
    np.save('dbg/mask3.npy',m); print('area',m.sum())
    m1=np.load('dbg/mask1.npy'); print('added vs mask1',int(((m==1)&(m1==0)).sum()),'removed',int(((m==0)&(m1==1)).sum()))
    # difference visualisation
    vis=im.copy(); vis[(m==1)&(m1==0)]=(0,255,0); vis[(m==0)&(m1==1)]=(0,0,255)
    cv2.imwrite('dbg/mask3_diff.jpg',cv2.resize(vis[560:1740,120:1820],None,fx=0.9,fy=0.9,interpolation=cv2.INTER_AREA))
