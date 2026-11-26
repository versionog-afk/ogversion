import cv2,numpy as np,sys
SRC='work3d/ref/print-closeup.jpg'
def zoom(x0,y0,x1,y1,k,out,pts=None,img=None,grid=50):
    im=cv2.imread(SRC) if img is None else img
    c=im[y0:y1,x0:x1]
    c=cv2.resize(c,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
    # ticks every `grid` source px
    for x in range((x0//grid+1)*grid,x1,grid):
        X=(x-x0)*k; cv2.line(c,(X,0),(X,10),(0,255,255),1); cv2.putText(c,str(x),(X+2,22),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,255),1)
    for y in range((y0//grid+1)*grid,y1,grid):
        Y=(y-y0)*k; cv2.line(c,(0,Y),(10,Y),(0,255,255),1); cv2.putText(c,str(y),(12,Y+4),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,255),1)
    if pts is not None:
        for (px,py) in pts:
            cv2.circle(c,(int(round((px-x0)*k)),int(round((py-y0)*k))),4,(255,0,255),1)
    cv2.imwrite(out,c)
if __name__=='__main__':
    a=list(map(int,sys.argv[1:6])); zoom(*a,sys.argv[6])
