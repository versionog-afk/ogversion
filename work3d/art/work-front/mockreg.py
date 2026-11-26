# Register the (projectively rectified) photo lettering to the designer's flat mockup -> affine part of the rectification.
import cv2,numpy as np,sys
from lm import lm
from geom import rect_H,apply
SRC='work3d/ref/'
im=cv2.imread(SRC+'print-closeup.jpg'); mock=cv2.imread(SRC+'mockup-sheet.jpg').astype(np.float32)
main=np.load('dbg/main0.npy')
# fill holes except the A counter (largest hole)
inv=1-main; n,l,s,_=cv2.connectedComponentsWithStats(inv,4); out=l[0,0]
hid=[i for i in range(1,n) if i!=out]; big=max(hid,key=lambda i:s[i,4])
mask=np.where((l==out)|(l==big),0,1).astype(np.float32)
F0=float(sys.argv[1]) if len(sys.argv)>1 else 1922.0
H,th=rect_H(F0)
# rectified canvas: translate so the lettering sits inside
cn=apply(H,[(150,600),(1800,600),(1800,1700),(150,1700)]); t=-cn.min(0)+20; T=np.array([[1,0,t[0]],[0,1,t[1]],[0,0,1.0]])
HR=T@H; size=tuple(np.ceil(cn.max(0)+t+20).astype(int))
gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
gray_lin=gray**2.2
R_l=cv2.warpPerspective(gray*mask,HR,size,flags=cv2.INTER_LINEAR)
R_m=cv2.warpPerspective(mask,HR,size,flags=cv2.INTER_LINEAR)
print('rectified size',size,'tilt',th)
def target(kind):
    g=mock.mean(2)
    if kind=='black': c=g[808:876,430:516]; c=(c-24)/231.0; return c,(430,808)
    else: c=g[243:311,430:516]; return c,(430,243)
def sampler(img,sig):
    b=cv2.GaussianBlur(img,(0,0),sig)
    return b
def run(kind,use='lum',sig_list=(16,22,28,34)):
    tgt,(ox,oy)=target(kind)
    hh,ww=tgt.shape; yy,xx=np.mgrid[:hh,:ww].astype(np.float32)
    if kind=='grey':
        # dark lettering on light shirt: use silhouette (mask) against (bg - value)
        bg=np.median(tgt); tg=(bg-tgt)/bg
    else: tg=tgt
    best=None
    for sig in sig_list:
        src=sampler(R_l if use=='lum' else R_m,sig)
        ys,xs=np.where(R_m>0.5); x0,x1,y0,y1=xs.min(),xs.max(),ys.min(),ys.max()
        # initial affine: mock px -> rectified px   (bbox to bbox)
        ty,tx=np.where(tg>0.35*tg.max()); mx0,mx1,my0,my1=tx.min(),tx.max()+1,ty.min(),ty.max()+1
        sx=(x1-x0)/(mx1-mx0); sy=(y1-y0)/(my1-my0)
        p0=np.array([sx,0,x0-sx*mx0, 0,sy,y0-sy*my0])
        w=np.ones_like(tg)
        def res(p):
            mapx=p[0]*(xx+0.5)+p[1]*(yy+0.5)+p[2]; mapy=p[3]*(xx+0.5)+p[4]*(yy+0.5)+p[5]
            s=cv2.remap(src,mapx.astype(np.float32),mapy.astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
            a=s-s.mean(); b=tg-tg.mean()
            a/=np.sqrt((a*a).mean())+1e-9; b/=np.sqrt((b*b).mean())+1e-9
            return (a-b).ravel()
        p,r=lm(res,p0,scale=[0.5,0.5,10,0.5,0.5,10],iters=120,h=0.2)
        p,r=lm(res,p,scale=[0.5,0.5,10,0.5,0.5,10],iters=60,h=0.05)
        ncc=1-0.5*np.mean(r*r)
        if best is None or ncc>best[0]: best=(ncc,sig,p)
        print(kind,use,'sigma',sig,'ncc %.4f'%ncc,'affine',np.round(p,3))
    return best
def decomp(p):
    A=np.array([[p[0],p[1]],[p[3],p[4]]])       # mock -> rectified
    Ai=np.linalg.inv(A)                          # rectified -> mock (what must be applied to the rectified photo)
    U,S,Vt=np.linalg.svd(Ai)
    # express as: rotation * stretch;  stretch ratio and direction (in rectified frame)
    ratio=S[0]/S[1]; v=Vt[0]; ang=np.degrees(np.arctan2(v[1],v[0]))
    # effect on axes: x-scale, y-scale, shear
    sx=np.linalg.norm(Ai[:,0]); sy=np.linalg.norm(Ai[:,1]); 
    cosang=(Ai[:,0]@Ai[:,1])/(sx*sy)
    rot=np.degrees(np.arctan2(Ai[1,0],Ai[0,0]))
    return dict(ratio=ratio,stretch_dir_deg=ang,sy_over_sx=sy/sx,axis_angle=np.degrees(np.arccos(cosang)),rot_x_axis=rot)
if __name__=='__main__':
    for kind,use in (('black','lum'),('black','mask'),('grey','mask'),('grey','lum')):
        b=run(kind,use)
        d=decomp(b[2]); print('  ->',kind,use,'best ncc %.4f sig %d'%(b[0],b[1]),{k:round(float(v),4) for k,v in d.items()})
        np.save('dbg/mockreg_%s_%s.npy'%(kind,use),b[2])
