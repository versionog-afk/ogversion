import numpy as np,cv2,sys
from edges import *
from geom import rect_H,apply
NOTES={
 'n1_A_bar_50':   dict(c=[(847,1150),(1132,1169),(1130,1327),(833,1308)],asp=140/77),
 'n2_N_top_50':   dict(c=[(320,702),(475,658),(553,900),(398,958)],asp=140/77),
}
if __name__=='__main__':
    for k,v in NOTES.items():
        C,L=quad(v['c']); v['C']=C
        show('dbg/fit_%s.png'%k,C,L)
        print(k,'corners',C.round(1).tolist(),'edge rms',[round(l[2],2) for l in L],'n',[l[3] for l in L])
    for f in (600,961,1300,1600,1922,2300,2800):
        H,th=rect_H(f); row=[]
        for k,v in NOTES.items():
            q=apply(H,v['C']); e=[q[(i+1)%4]-q[i] for i in range(4)]
            ln=[np.linalg.norm(x) for x in e]
            ang=[np.degrees(np.arccos(np.clip(-(e[i-1]@e[i])/(ln[i-1]*ln[i]),-1,1))) for i in range(4)]
            a=(ln[0]+ln[2])/(ln[1]+ln[3]); a=max(a,1/a)
            par=[np.degrees(np.arccos(np.clip(abs(e[0]@e[2])/(ln[0]*ln[2]),-1,1))),np.degrees(np.arccos(np.clip(abs(e[1]@e[3])/(ln[1]*ln[3]),-1,1)))]
            row.append('%s asp %.3f (true %.3f) angles %s nonpar %s'%(k,a,v['asp'],np.round(ang,1),np.round(par,1)))
        print('f',f,'tilt %.1f'%th,' | '.join(row))
