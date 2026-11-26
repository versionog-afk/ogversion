import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC)
lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
L=lab[...,0]; C=np.hypot(lab[...,1]-128,lab[...,2]-128)
Lb=cv2.GaussianBlur(L,(0,0),2.5); Cb=cv2.GaussianBlur(C,(0,0),3.0)
cand=((Lb>140)|((Cb>16)&(Lb>50))).astype(np.uint8)
n,lbl,st,_=cv2.connectedComponentsWithStats(cand,8)
order=np.argsort(-st[1:,4])+1
print([(int(i),st[i].tolist()) for i in order[:12]])
np.save('dbg/cand.npy',cand)
vis=im.copy()
cnts,_=cv2.findContours(cand,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
cv2.drawContours(vis,cnts,-1,(0,255,0),1)
cv2.imwrite('dbg/cand_overlay.png',vis[500:1800,100:1900])
cv2.imwrite('dbg/cand_small.png',cv2.resize(cand*255,None,fx=0.5,fy=0.5,interpolation=cv2.INTER_AREA))
