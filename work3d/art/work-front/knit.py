import cv2,numpy as np
SRC='work3d/ref/print-closeup.jpg'
im=cv2.imread(SRC); g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
main=np.load('dbg/main0.npy')
far=cv2.dilate(main,np.ones((61,61),np.uint8))
N=192
win=np.outer(np.hanning(N),np.hanning(N))
res=[]
for y in range(96,2560-96,96):
    for x in range(96,1920-96,96):
        if far[y-96:y+96,x-96:x+96].any(): continue
        p=g[y-96:y+96,x-96:x+96]; p=(p-p.mean())*win
        F=np.abs(np.fft.fftshift(np.fft.fft2(p,(512,512))))
        # zero DC neighbourhood
        cy=cx=256
        yy,xx=np.mgrid[:512,:512]; r=np.hypot(yy-cy,xx-cx)
        F[r<14]=0
        # wale peak: near horizontal axis (|fy|<|fx|*0.35), fx>0
        mw=(xx>cx)&(np.abs(yy-cy)<0.35*(xx-cx))
        Fw=np.where(mw,F,0); iy,ix=np.unravel_index(Fw.argmax(),F.shape)
        fx,fy=(ix-cx)/512,(iy-cy)/512
        # course peak: near vertical axis
        mc=(yy>cy)&(np.abs(xx-cx)<0.35*(yy-cy))
        Fc=np.where(mc,F,0); jy,jx=np.unravel_index(Fc.argmax(),F.shape)
        gx,gy=(jx-cx)/512,(jy-cy)/512
        res.append((x,y,fx,fy,Fw.max()/F.mean(),gx,gy,Fc.max()/F.mean()))
res=np.array(res)
np.save('dbg/knit.npy',res)
for r in res:
    print('x%4d y%4d  wale period %.2f px ang %.1f (snr %.0f) | course period %.2f px ang %.1f (snr %.0f)'%(r[0],r[1],1/np.hypot(r[2],r[3]),np.degrees(np.arctan2(r[3],r[2])),r[4],1/np.hypot(r[5],r[6]),np.degrees(np.arctan2(r[5],r[6])),r[7]))
