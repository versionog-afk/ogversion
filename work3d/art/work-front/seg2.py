# Stage 1 of the matte: automatic silhouette (bright or chromatic ink), closed, hole-filled, A-counter kept open.
import cv2,numpy as np
from tiles import tiles
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC)
lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
L=lab[...,0]; C=np.hypot(lab[...,1]-128,lab[...,2]-128)
Ls=cv2.GaussianBlur(L,(0,0),1.6); Cs=cv2.GaussianBlur(C,(0,0),2.5)
def build(tL=142,tC=14,tL2=48,close_r=4):
    cand=((Ls>tL)|((Cs>tC)&(Ls>tL2))).astype(np.uint8)
    # restrict to the neighbourhood of the lettering (the far cloth is irrelevant)
    roi=np.zeros_like(cand); roi[590:1710,140:1800]=1; cand&=roi
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*close_r+1,2*close_r+1))
    c2=cv2.morphologyEx(cand,cv2.MORPH_CLOSE,k)
    n,l,s,_=cv2.connectedComponentsWithStats(c2,8)
    main=(l==(np.argmax(s[1:,4])+1)).astype(np.uint8)
    # holes: fill all but the A counter (identified by position: contains the point (990,1075))
    inv=1-main; n2,l2,s2,_=cv2.connectedComponentsWithStats(inv,4)
    keep_open={l2[0,0],l2[1075,990]}
    m=np.where(np.isin(l2,list(keep_open)),0,1).astype(np.uint8)
    # opening of the outside by a 1px disc removes hairline cuts into the ink
    return m
if __name__=='__main__':
    m=build(); np.save('dbg/mask2.npy',m); print(m.sum(), 'A counter open:', m[1075,990]==0)
    tiles(m,'dbg/t2')
