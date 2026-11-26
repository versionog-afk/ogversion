# Where is the caption relative to the map?  Map caption ink into mock space with each frame's homography.
from common import *
import json
from reg1 import ink_of_gray, load
d=json.load(open('reg1.json'))
def cap_pts(key):
    g,off=load(key)
    shirt,ink,bb=ink_of_gray(g)
    x,y,w,h=bb
    n,lab,st,cen=cv2.connectedComponentsWithStats(ink,connectivity=8)
    pts=[]
    for k in range(1,n):
        cx,cy=cen[k]; a=st[k,cv2.CC_STAT_AREA]
        if cy>y+h*1.03 and cy<y+h*1.40 and x-0.1*w<cx<x+w*1.1 and a>12 and st[k,cv2.CC_STAT_HEIGHT]<0.12*h:
            ys,xs=np.nonzero(lab==k); pts.append(np.stack([xs+off[0],ys+off[1]],1))
    if not pts: return None
    return np.concatenate(pts).astype(np.float64)
def to_mock(key,P):
    H=np.array(d[key]['H'])@np.diag([3.0,3.0,1.0])   # mock px -> source
    Hi=np.linalg.inv(H)
    q=(Hi@np.c_[P,np.ones(len(P))].T).T
    return q[:,:2]/q[:,2:3]
if __name__=='__main__':
    out={}
    for key in ['wb']+[str(i) for i in list(range(57,92,2))+list(range(99,142,2))]:
        P=cap_pts(key)
        if P is None or len(P)<200: print(key,'no caption'); continue
        Q=to_mock(key,P)
        # principal axis
        c=Q.mean(0); u,s,vt=np.linalg.svd(Q-c,full_matrices=False)
        ax=vt[0]; 
        if ax[0]<0: ax=-ax
        ang=np.degrees(np.arctan2(ax[1],ax[0]))
        t=(Q-c)@ax; nrm=(Q-c)@np.array([-ax[1],ax[0]])
        L=np.percentile(t,99.8)-np.percentile(t,0.2); Hh=np.percentile(nrm,99)-np.percentile(nrm,1)
        mid=c+ax*(np.percentile(t,99.8)+np.percentile(t,0.2))/2
        out[key]=dict(cx=float(mid[0]),cy=float(mid[1]),ang=float(ang),L=float(L),h=float(Hh),n=int(len(P)))
        print(key,'centre (%.1f,%.1f) ang %.2f len %.1f height %.1f  npix %d'%(mid[0],mid[1],ang,L,Hh,len(P)))
    json.dump(out,open('caption_geo.json','w'))
