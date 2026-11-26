import cv2,numpy as np
from geom import rect_H,apply
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC)
def rectified(f,pad=40):
    H,th=rect_H(f)
    cn=apply(H,[(150,600),(1800,600),(1800,1700),(150,1700)]); t=-cn.min(0)+pad
    T=np.array([[1,0,t[0]],[0,1,t[1]],[0,0,1.0]]); HR=T@H
    size=tuple(int(v) for v in np.ceil(cn.max(0)+t+pad))
    return cv2.warpPerspective(im,HR,size,flags=cv2.INTER_CUBIC),HR
if __name__=='__main__':
    R,HR=rectified(1922.0); cv2.imwrite('dbg/rect1922.png',R); np.save('dbg/HR1922.npy',HR); print(R.shape)
    cv2.imwrite('dbg/rect1922_small.jpg',cv2.resize(R,None,fx=0.5,fy=0.5,interpolation=cv2.INTER_AREA))
