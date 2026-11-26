# Stage 1 + 2 of the front matte, on the source pixel grid of print-closeup.jpg.
#   stage 1: silhouette  = automatic mask (seg5) + hand-drawn patches judged by eye (PATCH_ADD / PATCH_CUT)
#   stage 2: sub-pixel edge = local two-colour matte (ink colour vs. rim colour) in a narrow band round the stage-1 contour
import cv2,numpy as np
from seg5 import features,auto_mask,tidy,fill,SRC
# polygons in source pixel coordinates (x,y); each one was decided by looking at 3-4x enlargements
PATCH_ADD={
 'A right leg, orange stack in shadow under the 20 note':[(1116,1606),(1250,1598),(1250,1612),(1222,1621),(1195,1631),(1160,1643),(1130,1653),(1122,1650),(1117,1630)],
 '2 base, red stack lobe under the 5 note':[(1526,1637),(1570,1630),(1608,1628),(1607,1655),(1602,1674),(1588,1669),(1562,1656),(1540,1647)],
 'N left leg, dim notes of the stack under the 50 note':[(200,1590),(390,1590),(388,1602),(362,1612),(300,1610),(250,1617),(214,1604)],
 '2 hook, dark side of the orange note edge':[(1455,845),(1458,870),(1460,890),(1463,925),(1466,935),(1476,935),(1470,890),(1462,850)],
}
PATCH_CUT={}
A_COUNTER=(990,1075)     # a point inside the triangle of the A (stays open)
def stage1():
    im,L,C=features()
    m=tidy(auto_mask(L,C))
    for name,p in PATCH_ADD.items(): cv2.fillPoly(m,[np.array(p,np.int32)],1)
    for name,p in PATCH_CUT.items(): cv2.fillPoly(m,[np.array(p,np.int32)],0)
    m=fill(m,(A_COUNTER,))
    n,l,s,_=cv2.connectedComponentsWithStats(m,8); m=(l==(np.argmax(s[1:,4])+1)).astype(np.uint8)
    return im,m
def norm_conv(img,w,sig):
    num=cv2.GaussianBlur(img*w[...,None],(0,0),sig); den=cv2.GaussianBlur(w,(0,0),sig)
    return num/np.maximum(den[...,None],1e-6),den
def stage2(im,m,inner=2.0,outer=3.0,sigF=3.0,sigB=2.5):
    """Returns alpha (float32, source grid) and F (ink colour extended outwards, float32 BGR 0..255)."""
    I=im.astype(np.float32)
    Is=cv2.GaussianBlur(I,(0,0),0.6)
    d_in=cv2.distanceTransform(m,cv2.DIST_L2,5)                 # >0 inside
    d_out=cv2.distanceTransform(1-m,cv2.DIST_L2,5)              # >0 outside
    sure_f=(d_in>=inner+1).astype(np.float32); sure_b=(d_out>=outer+1).astype(np.float32)
    # local ink colour from just inside the edge, local rim colour from just outside (weights fade with distance from the edge)
    wf=sure_f*np.exp(-np.maximum(d_in-(inner+1),0)/3.0); wb=sure_b*np.exp(-np.maximum(d_out-(outer+1),0)/2.5)
    F,_=norm_conv(I,wf,sigF); B,_=norm_conv(I,wb,sigB)
    FB=F-B; den=(FB*FB).sum(2)
    a=((Is-B)*FB).sum(2)/np.maximum(den,1e-3)
    a=np.clip(a,0,1)
    # where ink and rim are too alike the estimate is meaningless: fall back to the smoothed stage-1 mask
    conf=np.clip((np.sqrt(den)-30)/50,0,1)
    soft=cv2.GaussianBlur(m.astype(np.float32),(0,0),0.9)
    a=conf*a+(1-conf)*soft
    alpha=np.where(d_in>=inner,1.0,np.where(d_out>=outer,0.0,a)).astype(np.float32)
    # blend into the forced zones over half a pixel to avoid steps
    return alpha,F,B,d_in,d_out
if __name__=='__main__':
    im,m=stage1(); np.save('dbg/stage1.npy',m)
    alpha,F,B,d_in,d_out=stage2(im,m)
    np.save('dbg/alpha_src.npy',alpha)
    cv2.imwrite('dbg/alpha_src.png',(alpha*255).round().astype(np.uint8))
    print('stage1 area',int(m.sum()),'alpha sum',float(alpha.sum()),'alpha>0.5 area',int((alpha>0.5).sum()))
    band=(d_in<2)&(d_out<3)
    print('band px',int(band.sum()),'mean alpha in band %.3f'%alpha[band].mean())
