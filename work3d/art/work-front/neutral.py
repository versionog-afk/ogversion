import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC)
lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
L=lab[...,0]; C=np.hypot(lab[...,1]-128,lab[...,2]-128)
Ls=cv2.GaussianBlur(L,(0,0),2.0); Cs=cv2.GaussianBlur(C,(0,0),2.5)
m1=np.load('dbg/mask1.npy')              # filled silhouette (A counter open)
# convex-ish hull of the silhouette: closing with a big disc, to also see the bays
k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(81,81)); hull=cv2.morphologyEx(m1,cv2.MORPH_CLOSE,k)
dark=((Ls<135)&(Cs<9)&(hull>0)).astype(np.uint8)
dark=cv2.morphologyEx(dark,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
n,l,s,cen=cv2.connectedComponentsWithStats(dark,8)
vis=im.copy()
vis[dark>0]=(0.45*vis[dark>0]+0.55*np.array([255,0,255])).astype(np.uint8)
rows=[]
for i in np.argsort(-s[1:,4])[:60]+1:
    x,y,w,h,a=s[i]
    if a<120: continue
    inside=m1[l==i].mean()
    rows.append((i,x,y,w,h,a,inside,Ls[l==i].mean(),Cs[l==i].mean(),(lab[...,1][l==i]-128).mean(),(lab[...,2][l==i]-128).mean()))
    cv2.putText(vis,str(len(rows)-1),(x+w//2-6,y+h//2+5),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,255),1)
for k_,r in enumerate(rows): print(k_,'bbox',r[1:5],'area',r[5],'inside-filled %.2f'%r[6],'L %.0f C %.1f a %.1f b %.1f'%r[7:])
cv2.imwrite('dbg/neutral_small.jpg',cv2.resize(vis[560:1740,120:1820],None,fx=0.9,fy=0.9,interpolation=cv2.INTER_AREA))
np.save('dbg/neutral_lbl.npy',l)
