import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC)
lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
L=lab[...,0]; C=np.hypot(lab[...,1]-128,lab[...,2]-128)
m1=np.load('dbg/mask1.npy')
# statistics of the rim: band 3..9 px outside the preliminary mask
d_out=cv2.distanceTransform((1-m1).astype(np.uint8),cv2.DIST_L2,5)
rim=(d_out>3)&(d_out<9)
cloth=(d_out>25)&(d_out<60)
Ls=cv2.GaussianBlur(L,(0,0),1.2); Cs=cv2.GaussianBlur(C,(0,0),2.0)
for nm,r in (('rim',rim),('cloth',cloth)):
    print(nm,'L p5/50/95',np.percentile(Ls[r],[5,50,95]).round(1),'C p50/95/99',np.percentile(Cs[r],[50,95,99]).round(1))
d_in=cv2.distanceTransform(m1,cv2.DIST_L2,5)
edge_in=(d_in>2)&(d_in<8)
print('note band 2..8 px inside: L p5/25/50',np.percentile(Ls[edge_in],[5,25,50]).round(1),'C p5/50',np.percentile(Cs[edge_in],[5,50]).round(1))
# rim brightness varies with lighting: map the local rim level
ys,xs=np.where(rim)
print('rim L by image region:')
for y0 in range(600,1700,220):
    print(y0,[int(np.median(Ls[rim&(np.arange(2560)[:,None]>=y0)&(np.arange(2560)[:,None]<y0+220)&(np.arange(1920)[None]>=x0)&(np.arange(1920)[None]<x0+400)])) if (rim[y0:y0+220,x0:x0+400]).sum()>50 else -1 for x0 in range(150,1800,400)])
