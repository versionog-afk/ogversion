import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC)
lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
labs=cv2.GaussianBlur(lab,(0,0),1.5)
def fit_edge(p0,p1,half=9,shrink=0.1,step=1.0):
    """Sub-pixel straight edge near segment p0-p1 (source px). Returns (point, unit dir, rms, n)."""
    p0=np.array(p0,float); p1=np.array(p1,float); d=p1-p0; Ln=np.linalg.norm(d); d/=Ln; nrm=np.array([-d[1],d[0]])
    ts=np.arange(shrink*Ln,(1-shrink)*Ln,step); offs=np.arange(-half,half+0.01,0.5)
    pts=[]
    for t in ts:
        q=p0+d*t; xs=(q[0]+offs*nrm[0]).astype(np.float32)[None]; ys=(q[1]+offs*nrm[1]).astype(np.float32)[None]
        prof=cv2.remap(labs,xs,ys,cv2.INTER_LINEAR)[0]          # (n,3)
        gmag=np.linalg.norm(np.gradient(prof,axis=0),axis=1)
        i=int(np.argmax(gmag[2:-2]))+2
        # parabolic refinement
        a,b,c=gmag[i-1],gmag[i],gmag[i+1]; den=a-2*b+c; sub=0.5*(a-c)/den if abs(den)>1e-9 else 0
        pts.append((q+nrm*(offs[i]+sub*0.5), b))
    P=np.array([p for p,_ in pts]); wgt=np.array([w for _,w in pts])
    keep=wgt>np.percentile(wgt,20)
    for it in range(4):
        c0=P[keep].mean(0); u,s,vt=np.linalg.svd(P[keep]-c0); dirv=vt[0]; nn=np.array([-dirv[1],dirv[0]])
        r=(P-c0)@nn; sd=np.sqrt(np.mean(r[keep]**2)); keep=(np.abs(r)<max(2.0*sd,0.6))&(wgt>np.percentile(wgt,20))
    if dirv@d<0: dirv=-dirv
    return c0,dirv,sd,int(keep.sum()),P[keep]
def isect(l1,l2):
    (c1,d1),(c2,d2)=l1,l2
    A=np.array([d1,-d2]).T; t=np.linalg.solve(A,c2-c1); return c1+d1*t[0]
def quad(corners,**kw):
    """corners: approx TL,TR,BR,BL (any order around). Returns refined corners + edge fits."""
    L=[]
    for i in range(4):
        c0,dv,sd,n,P=fit_edge(corners[i],corners[(i+1)%4],**kw); L.append((c0,dv,sd,n,P))
    out=[isect((L[i-1][0],L[i-1][1]),(L[i][0],L[i][1])) for i in range(4)]
    return np.array(out),L
def show(name,corners,L,pad=30,k=3):
    x0,y0=np.floor(corners.min(0)-pad).astype(int); x1,y1=np.ceil(corners.max(0)+pad).astype(int)
    c=cv2.resize(im[y0:y1,x0:x1],None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
    for i in range(4):
        a=((corners[i]-[x0,y0])*k).astype(int); b=((corners[(i+1)%4]-[x0,y0])*k).astype(int)
        cv2.line(c,tuple(a),tuple(b),(255,0,255),1,cv2.LINE_AA)
        for p in L[i][4][::4]: cv2.circle(c,tuple(((p-[x0,y0])*k).astype(int)),1,(0,255,0),-1)
    cv2.imwrite(name,c)
