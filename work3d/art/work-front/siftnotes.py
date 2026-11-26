import cv2,numpy as np
R=cv2.imread('dbg/rect1922.png')
g=cv2.cvtColor(R,cv2.COLOR_BGR2GRAY)
g=cv2.GaussianBlur(g,(0,0),2.0)      # suppress knit texture
sift=cv2.SIFT_create(nfeatures=0,contrastThreshold=0.02,edgeThreshold=12,sigma=1.6)
def feats(x0,y0,x1,y1):
    m=np.zeros(g.shape,np.uint8); m[y0:y1,x0:x1]=255
    k,d=sift.detectAndCompute(g,m); return k,d
def match(a,b,name):
    ka,da=feats(*a); kb,db=feats(*b)
    bf=cv2.BFMatcher(cv2.NORM_L2)
    mm=bf.knnMatch(da,db,k=2)
    good=[m for m,n in mm if m.distance<0.8*n.distance]
    if len(good)<6: print(name,'too few matches',len(good),len(ka),len(kb)); return None
    pa=np.float32([ka[m.queryIdx].pt for m in good]); pb=np.float32([kb[m.trainIdx].pt for m in good])
    M,inl=cv2.estimateAffine2D(pa,pb,method=cv2.RANSAC,ransacReprojThreshold=4.0,maxIters=20000,confidence=0.999)
    if M is None: print(name,'no model'); return None
    inl=inl.ravel().astype(bool)
    A=M[:,:2]; U,S,Vt=np.linalg.svd(A)
    rot=np.degrees(np.arctan2(A[1,0],A[0,0]))
    print(name,'feats',len(ka),len(kb),'good',len(good),'inliers',inl.sum(),'sv',S.round(4),'ratio %.4f'%(S[0]/S[1]),'rot %.1f'%rot,'det %.3f'%np.linalg.det(A))
    return M,pa[inl],pb[inl]
n1=(880,790,1250,1040)
cands={'N_bl_50':(200,880,500,1340),'N_top_50':(250,120,570,600),'A_r_50':(1050,440,1300,720),'A_top_50':(980,100,1230,520),'two_tl_50':(1330,150,1640,470),'whole':(150,60,1950,1400)}
for k,v in cands.items(): match(n1,v,k)
print('--- details')
def solve_d(M):
    A=M[:,:2]
    # find D=diag(1,d) and shear-free model: D^-1 A D should be a similarity -> minimise deviation over d
    best=None
    for d in np.linspace(0.8,1.25,901):
        D=np.diag([1,d]); B=np.linalg.inv(D)@A@D; S=np.linalg.svd(B,compute_uv=False); r=S[0]/S[1]
        if best is None or r<best[1]: best=(d,r)
    return best
for k,v in cands.items():
    if k=='whole': continue
    r=match(n1,v,k)
    if r is None: continue
    M,pa,pb=r
    print('   M',M[:,:2].round(3).tolist(),'|M ex| %.3f |M ey| %.3f'%(np.linalg.norm(M[:,0]),np.linalg.norm(M[:,1])),'best d (rect_y = d * true_y): %.3f residual ratio %.3f'%solve_d(M))
