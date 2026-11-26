import numpy as np, cv2
CX,CY=960.0,1280.0
Q=np.load('work3d/art/work-front/dbg/knitfit.npy')
G,Hh=Q[0],Q[1]          # vanishing line of the cloth plane: G*x + Hh*y + 1 = 0  (from the knit)
def rect_H(f,cx=CX,cy=CY,g=G,h=Hh):
    """Metric rectification (up to similarity) of the cloth plane for focal length f [px]."""
    K=np.array([[f,0,cx],[0,f,cy],[0,0,1.0]])
    n=K.T@np.array([g,h,1.0]); n/=np.linalg.norm(n)
    if n[2]<0: n=-n
    z=np.array([0,0,1.0]); v=np.cross(n,z); s=np.linalg.norm(v); c=n@z
    if s<1e-12: R=np.eye(3)
    else:
        vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
        R=np.eye(3)+vx+vx@vx*((1-c)/s**2)
    H=K@R@np.linalg.inv(K)
    return H/H[2,2], np.degrees(np.arccos(c))
def apply(H,pts):
    p=np.c_[np.asarray(pts,float),np.ones(len(pts))]@H.T
    return p[:,:2]/p[:,2:3]
if __name__=='__main__':
    main=np.load('dbg/main0.npy')
    cnts,_=cv2.findContours(main,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    P=cnts[0][:,0,:].astype(float)
    print('raw bbox aspect',np.ptp(P[:,0])/np.ptp(P[:,1]))
    for f in (1000,1500,1922,2200,2500,2800,3200,3844,5000):
        H,th=rect_H(f); q=apply(H,P)
        # aspect at several rotations to find upright by min-area rect
        (c0,c1),(w,h),a=cv2.minAreaRect(q.astype(np.float32))
        print('f=%5d tilt %.1f deg  bbox aspect %.3f  minAreaRect %.3f ang %.1f  scale top/bottom check'%(f,th,np.ptp(q[:,0])/np.ptp(q[:,1]),max(w,h)/min(w,h),a))
