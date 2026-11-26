# Local knit frequency field -> projective part of the cloth-plane homography (vanishing line).
import cv2,numpy as np
from lm import lm
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC); g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
main=np.load('dbg/main0.npy')
far=cv2.dilate(main,np.ones((41,41),np.uint8))
N=160; P=1024
win=np.outer(np.hanning(N),np.hanning(N))
yy,xx=np.mgrid[:P,:P]; c=P//2
FX=(xx-c)/P; FY=(yy-c)/P
def peak(F,mask):
    Fm=np.where(mask,F,0); iy,ix=np.unravel_index(Fm.argmax(),F.shape)
    # sub-bin centroid in 5x5
    w=F[iy-2:iy+3,ix-2:ix+3]; 
    if w.shape!=(5,5): return None
    sx=(w*FX[iy-2:iy+3,ix-2:ix+3]).sum()/w.sum(); sy=(w*FY[iy-2:iy+3,ix-2:ix+3]).sum()/w.sum()
    return sx,sy,Fm.max()
W=[];Cc=[]
for y in range(N//2,2560-N//2,64):
    for x in range(N//2,1920-N//2,64):
        if far[y-N//2:y+N//2,x-N//2:x+N//2].mean()>0.0: continue
        p=g[y-N//2:y+N//2,x-N//2:x+N//2]; p=(p-p.mean())*win
        F=np.abs(np.fft.fftshift(np.fft.fft2(p,(P,P))))
        med=np.median(F)
        # predicted fundamental periods (linear models from the coarse scan)
        pw=0.0032*(y+3530); pc=0.0405*pw*pw
        ang=np.arctan2(FY,FX)
        r=np.hypot(FX,FY)
        mw=(np.abs(r-1/pw)<0.12/pw)&(np.abs(ang)<np.radians(25))
        mc=(np.abs(r-1/pc)<0.15/pc)&(np.abs(ang-np.pi/2)<np.radians(25))
        a=peak(F,mw); b=peak(F,mc)
        if a and a[2]/med>25: W.append((x,y,a[0],a[1],a[2]/med))
        if b and b[2]/med>12: Cc.append((x,y,b[0],b[1],b[2]/med))
W=np.array(W); Cc=np.array(Cc)
print(len(W),len(Cc))
np.save('dbg/knitW.npy',W); np.save('dbg/knitC.npy',Cc)
# model: phase gradient of X=(a x+b y)/(g x+h y+1)
def grad(p,x,y,gh):
    a,b=p; gg,hh=gh
    d=gg*x+hh*y+1; n=a*x+b*y
    return (a*d-n*gg)/d**2,(b*d-n*hh)/d**2
# include a constant c in numerator: X=(a x+b y+c)/d
def grad3(p,x,y,gh):
    a,b,c0=p; gg,hh=gh
    d=gg*x+hh*y+1; n=a*x+b*y+c0
    return (a*d-n*gg)/d**2,(b*d-n*hh)/d**2
def res(q):
    gh=q[:2]; pw=q[2:5]; pc=q[5:8]
    gx,gy=grad3(pw,W[:,0],W[:,1],gh); hx,hy=grad3(pc,Cc[:,0],Cc[:,1],gh)
    nw=np.hypot(W[:,2],W[:,3]); nc=np.hypot(Cc[:,2],Cc[:,3])
    return np.concatenate([(gx-W[:,2])/nw,(gy-W[:,3])/nw,(hx-Cc[:,2])/nc,(hy-Cc[:,3])/nc])
q0=np.array([0,1/3530.,1/15.,0,0,0,1/9.,0])
q,rr=lm(res,q0,scale=[1e-5,1e-5,1e-3,1e-3,1,1e-3,1e-3,1],robust=0.03)
print('g,h',q[:2],'vanishing line y at x=960:',-(1+q[0]*960)/q[1],'slope dy/dx',-q[0]/q[1])
print('wale params',q[2:5],'course params',q[5:8])
print('rms residual (relative)',np.sqrt(np.mean(rr**2)),'median abs',np.median(np.abs(rr)))
np.save('dbg/knitfit.npy',q)
