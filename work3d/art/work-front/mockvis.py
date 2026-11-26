import cv2,numpy as np,sys
import mockreg as M
def render(p,src,shape):
    hh,ww=shape; yy,xx=np.mgrid[:hh,:ww].astype(np.float32)
    mapx=p[0]*(xx+0.5)+p[1]*(yy+0.5)+p[2]; mapy=p[3]*(xx+0.5)+p[4]*(yy+0.5)+p[5]
    return cv2.remap(src,mapx.astype(np.float32),mapy.astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
tg,_=M.target('black')
rows=[]
for name,use,sig in (('black_lum','lum',34),('black_mask','mask',16)):
    p=np.load('dbg/mockreg_%s.npy'%name)
    src=cv2.GaussianBlur(M.R_l if use=='lum' else M.R_m,(0,0),sig)
    s=render(p,src,tg.shape)
    s=s/s.max(); t=tg/tg.max()
    row=np.hstack([t,s,np.abs(t-s)])
    rows.append(row)
big=np.vstack(rows)
cv2.imwrite('dbg/mockvis.png',cv2.resize((np.clip(big,0,1)*255).astype(np.uint8),None,fx=6,fy=6,interpolation=cv2.INTER_NEAREST))
