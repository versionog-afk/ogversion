import cv2,numpy as np,sys
SRC='work3d/ref/print-closeup.jpg'
_im=None
def zm(mask,x0,y0,x1,y1,k,out,grid=25,polys=None,gain=1.0):
    global _im
    if _im is None: _im=cv2.imread(SRC)
    c=_im[y0:y1,x0:x1].astype(np.float32)*gain
    c=cv2.resize(np.clip(c,0,255).astype(np.uint8),None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
    if mask is not None:
        mb=cv2.resize(mask[y0:y1,x0:x1].astype(np.uint8)*255,None,fx=k,fy=k,interpolation=cv2.INTER_NEAREST)
        cnts,_=cv2.findContours((mb>127).astype(np.uint8),cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(c,cnts,-1,(0,255,0),1)
    if polys:
        for p in polys:
            q=((np.array(p,float)-[x0,y0])*k).astype(np.int32); cv2.polylines(c,[q],True,(255,0,255),1)
    for x in range((x0//grid+1)*grid,x1,grid):
        X=(x-x0)*k; cv2.line(c,(X,0),(X,6),(0,255,255),1); cv2.putText(c,str(x),(X+2,16),cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,255,255),1)
    for y in range((y0//grid+1)*grid,y1,grid):
        Y=(y-y0)*k; cv2.line(c,(0,Y),(6,Y),(0,255,255),1); cv2.putText(c,str(y),(8,Y+4),cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,255,255),1)
    cv2.imwrite(out,c)
if __name__=='__main__':
    m=np.load(sys.argv[1]); a=list(map(int,sys.argv[2:7])); zm(m,*a,sys.argv[7],gain=float(sys.argv[8]) if len(sys.argv)>8 else 1.0)
