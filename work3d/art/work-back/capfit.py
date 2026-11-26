# Caption in mock space (homography only): fit JetBrains Mono ExtraBold with free horizontal stretch
from common import *
import json, sys
from reg2 import src_gray, norm_ink
from gridfit import gridfit
from multiprocessing import Pool
d=json.load(open('reg1.json'))
X0,X1,Y0,Y1=0,270,258,302
def cap_patch(key,Kc=7):
    g=src_gray(key)
    H=np.array(d[key]['H'])@np.diag([3.0/Kc,3.0/Kc,1.0])@np.array([[1,0,X0*Kc],[0,1,Y0*Kc],[0,0,1.0]])
    w=(X1-X0)*Kc; h=(Y1-Y0)*Kc
    out=cv2.warpPerspective(g,H,(w,h),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP)
    return norm_ink(out)
def one(key):
    p=cap_patch(key)
    b=gridfit(p,'ŠILAINIAI, KAUNAS','JetBrains Mono','ExtraBold',np.arange(62,92.1,2.0),np.arange(0.96,1.36,0.02),[0,2,4],[-3,-2,-1,0,1,2,3,4],blur=2.0)
    return key,b,p
if __name__=='__main__':
    keys=['wb']+[str(i) for i in list(range(57,96,4))+list(range(99,142,2))]
    with Pool(4) as pool: res=pool.map(one,keys)
    out={}
    for key,b,p in res:
        print(key,'ncc %.3f cap %.1f stretch %.2f dil %.1f ang %.1f'%b[:5],'loc',b[5],flush=True)
        out[key]=[float(v) for v in b[:5]]+list(b[5])+list(b[6])
        cv2.imwrite('cap_patch_%s.png'%key,(p*255).astype(np.uint8)) if key in ('wb','61','101','121','129','137') else None
    json.dump(out,open('capfit.json','w'))
