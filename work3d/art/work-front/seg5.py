# Stage 1 (automatic silhouette), edge-preserving version.
import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
def features():
    im=cv2.imread(SRC)
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB)
    f=lab
    for _ in range(2): f=cv2.bilateralFilter(f,9,18,3.5)      # smooths knit texture / JPEG chroma noise, keeps the note edges
    f=f.astype(np.float32)
    L=f[...,0]; C=np.hypot(f[...,1]-128,f[...,2]-128-2.2)
    return im,L,C
def auto_mask(L,C,tL=140,tC=16,wC=7.5,wLmin=46,reach=14):
    roi=np.zeros(L.shape,np.uint8); roi[585:1715,140:1800]=1
    strong=(((L>tL)|((C>tC)&(L>50)))&(roi>0)).astype(np.uint8)
    weak=((((C>wC)&(L>wLmin))&(roi>0))|(strong>0)).astype(np.uint8)
    n,l,s,_=cv2.connectedComponentsWithStats(strong,8); main=(l==(np.argmax(s[1:,4])+1)).astype(np.uint8)
    near=cv2.dilate(main,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*reach+1,2*reach+1)))
    n,l,s,_=cv2.connectedComponentsWithStats((weak&near).astype(np.uint8),8)
    ids=np.unique(l[main>0]); m=np.isin(l,ids[ids>0]).astype(np.uint8)
    return m
def tidy(m,close_r=3,open_r=2):
    k=lambda r:cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,k(close_r)); m=cv2.morphologyEx(m,cv2.MORPH_OPEN,k(open_r))
    n,l,s,_=cv2.connectedComponentsWithStats(m,8); return (l==(np.argmax(s[1:,4])+1)).astype(np.uint8)
def fill(m,open_pts=((990,1075),)):
    inv=1-m; n2,l2,s2,_=cv2.connectedComponentsWithStats(inv,4)
    keep={l2[0,0]}|{l2[y,x] for x,y in open_pts}
    return np.where(np.isin(l2,list(keep)),0,1).astype(np.uint8)
if __name__=='__main__':
    from tiles import tiles
    im,L,C=features()
    np.save('dbg/featL.npy',L); np.save('dbg/featC.npy',C)
    m=fill(tidy(auto_mask(L,C))); np.save('dbg/mask5.npy',m)
    m3=np.load('dbg/mask3.npy'); print('area',m.sum(),'added vs mask3',int(((m==1)&(m3==0)).sum()),'removed',int(((m==0)&(m3==1)).sum()))
    vis=im.copy(); vis[(m==1)&(m3==0)]=(0,255,0); vis[(m==0)&(m3==1)]=(0,0,255)
    cv2.imwrite('dbg/mask5_diff.jpg',cv2.resize(vis[560:1740,120:1820],None,fx=0.9,fy=0.9,interpolation=cv2.INTER_AREA))
    tiles(m,'dbg/b5',k=2,tw=480,th=230,x0=150,y0=1480,x1=1790,y1=1700)
    tiles(m,'dbg/h5',k=3,tw=300,th=200,x0=1280,y0=740,x1=1560,y1=930)
