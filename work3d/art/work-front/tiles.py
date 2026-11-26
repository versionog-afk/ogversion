import cv2,numpy as np,sys
SRC='work3d/ref/print-closeup.jpg'
def tiles(mask,prefix,k=2,tw=480,th=330,x0=150,y0=600,x1=1790,y1=1700,img=None,color=(0,255,0)):
    im=cv2.imread(SRC) if img is None else img
    big=cv2.resize(im,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
    mb=cv2.resize(mask.astype(np.uint8)*255,None,fx=k,fy=k,interpolation=cv2.INTER_LINEAR)
    cnts,_=cv2.findContours((mb>127).astype(np.uint8),cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(big,cnts,-1,color,1)
    names=[]
    idx=0
    ys=list(range(y0,y1,th)); xs=list(range(x0,x1,tw))
    for r,yy in enumerate(ys):
        for c,xx in enumerate(xs):
            t=big[yy*k:(yy+th)*k,xx*k:(xx+tw)*k].copy()
            cv2.putText(t,'%d,%d'%(xx,yy),(6,18),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,255),1)
            # ruler ticks each 50 source px
            for gx in range((xx//50+1)*50,xx+tw,50): cv2.line(t,((gx-xx)*k,t.shape[0]-8),((gx-xx)*k,t.shape[0]-1),(0,255,255),1); cv2.putText(t,str(gx),((gx-xx)*k+2,t.shape[0]-10),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,255,255),1)
            for gy in range((yy//50+1)*50,yy+th,50): cv2.line(t,(t.shape[1]-8,(gy-yy)*k),(t.shape[1]-1,(gy-yy)*k),(0,255,255),1); cv2.putText(t,str(gy),(t.shape[1]-40,(gy-yy)*k-2),cv2.FONT_HERSHEY_SIMPLEX,0.35,(0,255,255),1)
            n='%s_r%dc%d.png'%(prefix,r,c); cv2.imwrite(n,t); names.append(n)
    return names
if __name__=='__main__':
    main=np.load('dbg/main0.npy')
    inv=1-main; n,l,s,_=cv2.connectedComponentsWithStats(inv,4); out=l[0,0]
    hid=[i for i in range(1,n) if i!=out]; big=max(hid,key=lambda i:s[i,4])
    m=np.where((l==out)|(l==big),0,1).astype(np.uint8)
    np.save('dbg/mask1.npy',m)
    print(tiles(m,'dbg/t1'))
