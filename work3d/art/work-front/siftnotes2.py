import cv2,numpy as np
R=cv2.imread('dbg/rect1922.png')
g0=cv2.cvtColor(R,cv2.COLOR_BGR2GRAY)
def run(blur,seeds,thr=4.0,ratio=0.8):
    g=cv2.GaussianBlur(g0,(0,0),blur)
    sift=cv2.SIFT_create(contrastThreshold=0.015,edgeThreshold=14)
    kall,dall=sift.detectAndCompute(g,None)
    pall=np.float32([k.pt for k in kall])
    out=[]
    for name,(x0,y0,x1,y1) in seeds.items():
        ins=(pall[:,0]>=x0)&(pall[:,0]<x1)&(pall[:,1]>=y0)&(pall[:,1]<y1)
        ia=np.where(ins)[0]; ib=np.where(~((pall[:,0]>=x0-10)&(pall[:,0]<x1+10)&(pall[:,1]>=y0-10)&(pall[:,1]<y1+10)))[0]
        bf=cv2.BFMatcher(cv2.NORM_L2); mm=bf.knnMatch(dall[ia],dall[ib],k=5)
        # keep several candidate matches per feature (the same note type repeats many times)
        pa=[];pb=[]
        for ms in mm:
            for m in ms[:4]:
                if m.distance<ms[0].distance/ratio and m.distance<260: pa.append(pall[ia[m.queryIdx]]); pb.append(pall[ib[m.trainIdx]])
        pa=np.float32(pa); pb=np.float32(pb)
        left=np.ones(len(pa),bool)
        for rnd in range(8):
            if left.sum()<8: break
            M,inl=cv2.estimateAffine2D(pa[left],pb[left],method=cv2.RANSAC,ransacReprojThreshold=thr,maxIters=40000,confidence=0.999)
            if M is None: break
            inl=inl.ravel().astype(bool); idx=np.where(left)[0][inl]
            if len(idx)<8: break
            # require spatial spread of inliers in the seed
            spread=np.ptp(pa[idx],axis=0)
            A=M[:,:2]; S=np.linalg.svd(A,compute_uv=False); rot=np.degrees(np.arctan2(A[1,0]-A[0,1],A[0,0]+A[1,1]))
            best=None
            for d in np.linspace(0.8,1.25,901):
                D=np.diag([1,d]); B=np.linalg.inv(D)@A@D; s=np.linalg.svd(B,compute_uv=False); r=s[0]/s[1]
                if best is None or r<best[1]: best=(d,r)
            cen=pb[idx].mean(0)
            print('blur %.1f %-10s -> target centre (%4d,%4d) inl %3d spread %s rot %7.1f sv-ratio %.3f det %.2f | best d %.3f (resid %.3f)'%(blur,name,cen[0],cen[1],len(idx),spread.round(0),rot,S[0]/S[1],np.linalg.det(A),best[0],best[1]))
            out.append((name,cen,len(idx),rot,S[0]/S[1],best[0],M))
            left[idx]=False
    return out
seeds={'N_bl_50':(215,900,490,1330),'A_bar_50':(880,790,1250,1040),'A_l_20':(810,1010,990,1310),'A_r_20':(1140,1020,1320,1320),'N_10':(630,330,810,640),'two_100':(1560,1110,1860,1270),'N_top_50':(260,130,560,590),'two_20':(1370,820,1640,1160)}
if __name__=='__main__':
    for b in (1.6,2.4):
        run(b,seeds)
