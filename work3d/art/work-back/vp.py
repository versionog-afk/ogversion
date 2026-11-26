from common import *
import sys
def vp_vertical(gray, cx, cy, minlen=80, maxdev=12, label=''):
    lsd=cv2.createLineSegmentDetector(0)
    lines=lsd.detect(gray)[0][:,0,:]
    sel=[]
    for x1,y1,x2,y2 in lines:
        L=np.hypot(x2-x1,y2-y1); 
        if L<minlen: continue
        ang=np.degrees(np.arctan2(x2-x1,y2-y1)); ang=(ang+90)%180-90   # deviation from vertical
        if abs(ang)<maxdev: sel.append((x1,y1,x2,y2,L,ang))
    sel=np.array(sel)
    # each line: n.x = c ; solve for point minimizing weighted distances (RANSAC-ish robust)
    P1=sel[:,:2]; P2=sel[:,2:4]; d=P2-P1; d/=np.linalg.norm(d,axis=1)[:,None]
    n=np.stack([-d[:,1],d[:,0]],1); c=(n*P1).sum(1); w=sel[:,4]
    best=None
    rng=np.random.default_rng(0)
    for it in range(3000):
        i,j=rng.choice(len(sel),2,replace=False)
        A=np.array([n[i],n[j]]); 
        if abs(np.linalg.det(A))<1e-6: continue
        v=np.linalg.solve(A,[c[i],c[j]])
        # angular residual: angle between line dir and direction to vp from line midpoint
        mid=(P1+P2)/2; tv=v-mid; tv/=np.linalg.norm(tv,axis=1)[:,None]
        res=np.abs(tv[:,0]*d[:,1]-tv[:,1]*d[:,0])
        inl=res<np.sin(np.radians(0.6))
        sc=(w*inl).sum()
        if best is None or sc>best[0]: best=(sc,v,inl)
    sc,v,inl=best
    A=n[inl]*w[inl,None]; b=c[inl]*w[inl]
    v=np.linalg.lstsq(A,b,rcond=None)[0]
    return v,sel,inl
if __name__=='__main__':
    im=cv2.imread(SRC+'worn-back.png'); ph=im[468:1968]   # photo area
    g=cv2.cvtColor(ph,cv2.COLOR_BGR2GRAY)
    v,sel,inl=vp_vertical(g,562.5,750,minlen=70)
    print('wb vp',v,'n lines',len(sel),'inliers',inl.sum())
    for f in [900,1040,1127,1300]:
        print(f,'pitch deg',np.degrees(np.arctan2(f,(v[1]-750))))
    vis=ph.copy()
    for (x1,y1,x2,y2,L,a),k in zip(sel,inl):
        cv2.line(vis,(int(x1),int(y1)),(int(x2),int(y2)),(0,255,0) if k else (0,0,255),2)
    cv2.imwrite('vp_wb.jpg',vis)
    for i in [61,73,85,101,121,133]:
        fr=frame(i); g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY)
        try:
            v,sel,inl=vp_vertical(g,360,640,minlen=50)
            print(i,'vp',v,'n',len(sel),'inl',inl.sum(),'pitch(f=1050)',np.degrees(np.arctan2(1050,(v[1]-640))))
        except Exception as e: print(i,'fail',e)
