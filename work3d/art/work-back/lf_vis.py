import cv2, numpy as np, sys
from labelfit import *
m=cv2.imread('wmed3.png',0).astype(np.float32)/255
labs={'IX FORTAS':(450,408,0,26),'A1 HIGHWAY':(1210,450,34,30),'BALTŲ PR.#1':(712,735,62,28),'BALTŲ PR.#2':(690,1065,-17,28),
      'ŽEMAIČIŲ PL.':(950,1160,65,28),'BALTIJOS G.#1':(1405,950,-50,28),'BALTIJOS G.#2':(1225,1385,70,28)}
def rot_crop(img,cx,cy,ang,w,h,scale=2.0):
    M=cv2.getRotationMatrix2D((cx,cy),ang,scale); M[0,2]+=w/2-cx; M[1,2]+=h/2-cy
    return cv2.warpAffine(img,M,(w,h),flags=cv2.INTER_CUBIC)
def run(s,fam,style,tracking=0.0,out='lf.png',fit_stretch=False):
    S=cv2.resize(m,None,fx=1,fy=s,interpolation=cv2.INTER_CUBIC)
    rows=[]; res={}
    for name,(x,y,a,cap) in labs.items():
        text=name.split('#')[0]
        a2=np.degrees(np.arctan2(np.sin(np.radians(a))*s,np.cos(np.radians(a))))
        best=None
        for da in (-3,0,3):
          for dc in (0.9,1.0,1.1):
            p,sc=fit(S,text,fam,style,(x,y*s,a2+da,cap*dc*(1+(s-1)*0.5)),blur=1.2,tracking=tracking,fit_stretch=fit_stretch)
            if best is None or sc>best[1]: best=(p,sc)
        p,sc=best; res[name]=(p,sc)
        t=place(text,fam,style,p[0],p[1],p[2],p[3],S.shape,tracking,stretch=p[4])
        ov=np.zeros(S.shape+(3,),np.float32); ov[...,0]=S; ov[...,1]=S; ov[...,2]=S
        ov[...,2]=np.maximum(ov[...,2]*(1-0.6*t),t*0.9); ov[...,1]*=(1-0.6*t); ov[...,0]*=(1-0.6*t)
        c=rot_crop((ov*255).astype(np.uint8),p[0],p[1],p[2],760,120)
        cv2.putText(c,'%.3f cap %.1f ang %.1f st %.3f'%(sc,p[3],p[2],p[4]),(5,15),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,255,0),1)
        rows.append(c)
    cv2.imwrite(out,np.vstack(rows))
    return res
if __name__=='__main__':
    s=float(sys.argv[1]); fam=sys.argv[2]; style=sys.argv[3]; tr=float(sys.argv[4]) if len(sys.argv)>4 else 0.0
    res=run(s,fam,style,tr,'lf_%s_%s_%.2f.png'%(fam.replace(' ',''),style,s))
    for k,(p,sc) in res.items(): print(k,np.round(p,2),'%.4f'%sc)
