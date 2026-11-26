# Affine part of the rectification from the banknotes themselves:
# identical notes at different rotations must be related by similarities in the true artwork plane.
import cv2,numpy as np,sys
from rect0 import rectified
from lm import lm
F=float(sys.argv[1]) if len(sys.argv)>1 else 961.0
R,HR=rectified(F)
g0=cv2.cvtColor(R,cv2.COLOR_BGR2GRAY)
feats=[]
for blur in (1.4,2.0,2.8):
    g=cv2.GaussianBlur(g0,(0,0),blur)
    sift=cv2.SIFT_create(contrastThreshold=0.012,edgeThreshold=16)
    k,d=sift.detectAndCompute(g,None); feats.append((np.float32([x.pt for x in k]),d))
def box(pts,b): return (pts[:,0]>=b[0])&(pts[:,0]<b[2])&(pts[:,1]>=b[1])&(pts[:,1]<b[3])
def pair(a,b,name,thr0=5.0,thr1=3.0):
    PA=[];PB=[]
    for pts,d in feats:
        ia=np.where(box(pts,a))[0]; ib=np.where(box(pts,b))[0]
        if len(ia)<4 or len(ib)<4: continue
        mm=cv2.BFMatcher(cv2.NORM_L2).knnMatch(d[ia],d[ib],k=2)
        for m,n in mm:
            if m.distance<0.85*n.distance: PA.append(pts[ia[m.queryIdx]]); PB.append(pts[ib[m.trainIdx]])
    PA=np.float32(PA); PB=np.float32(PB)
    if len(PA)<8: print(name,'few',len(PA)); return None
    M,inl=cv2.estimateAffine2D(PA,PB,method=cv2.RANSAC,ransacReprojThreshold=thr0,maxIters=50000,confidence=0.9999)
    if M is None or inl.sum()<8: print(name,'fail'); return None
    # guided matching: all feature pairs consistent with M and with similar descriptors
    GA=[];GB=[]
    for pts,d in feats:
        ia=np.where(box(pts,a))[0]; ib=np.where(box(pts,b))[0]
        pr=pts[ia]@M[:,:2].T+M[:,2]
        for q,i in zip(pr,ia):
            dist=np.hypot(*(pts[ib]-q).T); c=np.where(dist<6.0)[0]
            if len(c)==0: continue
            dd=np.linalg.norm(d[ib[c]]-d[i],axis=1); j=c[np.argmin(dd)]
            if dd.min()<300: GA.append(pts[i]); GB.append(pts[ib[j]])
    GA=np.float32(GA); GB=np.float32(GB)
    for it in range(4):
        M2,inl2=cv2.estimateAffine2D(GA,GB,method=cv2.RANSAC,ransacReprojThreshold=thr1,maxIters=20000,confidence=0.999,refineIters=30)
        inl2=inl2.ravel().astype(bool)
    A=M2[:,:2]; S=np.linalg.svd(A,compute_uv=False); rot=np.degrees(np.arctan2(A[1,0]-A[0,1],A[0,0]+A[1,1]))
    # bootstrap
    idx=np.where(inl2)[0]; rng=np.random.default_rng(0); Ms=[]
    for bsi in range(200):
        s=rng.choice(idx,len(idx)); X=np.c_[GA[s],np.ones(len(s))]; sol,_,_,_=np.linalg.lstsq(X,GB[s],rcond=None); Ms.append(sol.T[:,:2])
    hull=cv2.convexHull(GA[idx]); area=cv2.contourArea(hull)
    print('%-22s inl %3d hull-area %6d rot %7.1f sv-ratio %.3f det %.3f'%(name,len(idx),area,rot,S[0]/S[1],np.linalg.det(A)))
    return dict(name=name,A=A,Ms=np.array(Ms),n=len(idx),rot=rot,area=area)
B={'A_bar_50':(880,790,1250,1040),'N_bl_50':(200,880,500,1340),'N_top_50':(250,120,570,600),'A_r_50':(1050,440,1300,720),
   'A_l_20':(800,1000,1000,1320),'A_r_20':(1130,1010,1330,1330),'N_10':(620,320,820,650),'two_10a':(1600,180,1840,420),'two_10b':(1600,580,1840,780),
   'N_l_20':(260,560,500,900),'A_tl_20':(860,560,1060,820),'two_20':(1360,800,1650,1170),'two_100':(1540,1090,1880,1290),'A_top_50':(980,100,1230,520),'two_tl_50':(1330,150,1640,470)}
# box coordinates were chosen on the f=1922 frame; rescale boxes to this frame through the homographies
from geom import rect_H,apply
R19,HR19=rectified(1922.0); Tm=HR@np.linalg.inv(HR19)
def conv(b):
    p=apply(Tm,[(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])]); return (p[:,0].min(),p[:,1].min(),p[:,0].max(),p[:,1].max())
B={k:conv(v) for k,v in B.items()}
pairs=[('A_bar_50','N_bl_50'),('A_bar_50','N_top_50'),('A_bar_50','A_r_50'),('N_bl_50','A_r_50'),('N_bl_50','N_top_50'),('A_r_50','N_top_50'),('A_bar_50','A_top_50'),('A_bar_50','two_tl_50'),
       ('A_l_20','A_r_20'),('A_l_20','N_l_20'),('A_l_20','A_tl_20'),('A_l_20','two_20'),('A_r_20','two_20'),('A_r_20','N_l_20'),('A_r_20','A_tl_20'),('N_l_20','two_20'),
       ('N_10','two_10a'),('N_10','two_10b'),('two_10a','two_10b')]
res=[]
for a,b in pairs:
    r=pair(B[a],B[b],a+'->'+b)
    if r: res.append(r)
    r=pair(B[b],B[a],b+'->'+a)
    if r: res.append(r)
np.save('dbg/notepairs_%d.npy'%int(F),np.array(res,dtype=object),allow_pickle=True)
