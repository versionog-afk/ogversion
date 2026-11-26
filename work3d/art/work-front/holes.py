import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC)
cand=np.load('dbg/cand.npy')
n,lbl,st,_=cv2.connectedComponentsWithStats(cand,8)
main=(lbl==(np.argmax(st[1:,4])+1)).astype(np.uint8)
inv=1-main
n2,l2,s2,_=cv2.connectedComponentsWithStats(inv,4)
outside=l2[0,0]
holes=[(i,s2[i]) for i in range(1,n2) if i!=outside]
holes.sort(key=lambda t:-t[1][4])
print(len(holes))
vis=im.copy()
for k,(i,s) in enumerate(holes[:60]):
    x,y,w,h,a=s
    print(k,i,x,y,w,h,a)
    cnts,_=cv2.findContours((l2==i).astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(vis,cnts,-1,(255,0,255),1)
    if a>150: cv2.putText(vis,str(k),(x+w//2-8,y+h//2+6),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2)
cnts,_=cv2.findContours(main,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
cv2.drawContours(vis,cnts,-1,(0,255,0),1)
np.save('dbg/main0.npy',main)
X0,Y0=140,580
for r in range(2):
    for c in range(3):
        cv2.imwrite(f'dbg/holes_{r}{c}.png',vis[Y0+r*560:Y0+r*560+600,X0+c*560:X0+c*560+600])
