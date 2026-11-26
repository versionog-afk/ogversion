# Fit a text string set in a given font to an image region by similarity transform (centre, angle, size)
from fonts import *
import cv2, numpy as np
_cache={}
def glyph_img(text,family,style,size=160,tracking=0.0):
    key=(text,family,style,size,tracking)
    if key not in _cache:
        f=ImageFont.truetype(fpath(family,style),size)
        asc,desc=f.getmetrics()
        adv=[f.getlength(c)+tracking*size for c in text]
        Wd=int(sum(adv))+size; Hh=asc+desc+size
        im=Image.new('L',(Wd,Hh),0); dr=ImageDraw.Draw(im)
        x=size/2; y0=size/2
        for c,a in zip(text,adv):
            dr.text((x,y0),c,font=f,fill=255); x+=a
        a=np.array(im).astype(np.float32)/255
        # reference point: centre of the cap-height box of the whole string (baseline = y0+asc ; cap height from font)
        from fontTools.ttLib import TTFont
        tt=TTFont(fpath(family,style)); upm=tt['head'].unitsPerEm
        cap=getattr(tt['OS/2'],'sCapHeight',0) or 0.7*upm
        caph=cap/upm*size
        base=y0+asc
        x0=size/2; x1=size/2+sum(adv)-tracking*size
        _cache[key]=(a,(x0,x1,base-caph,base),caph)
    return _cache[key]
def place(text,family,style,cx,cy,ang,capheight,shape,tracking=0.0,size=160,stretch=1.0,dil=0.0):
    """render text so that the centre of its cap box is at (cx,cy), rotated by ang degrees (clockwise in image coords, y down), cap height = capheight px.
    stretch: horizontal scale factor along the baseline."""
    a,(x0,x1,yt,yb),caph=glyph_img(text,family,style,size,tracking)
    if dil>0:
        k=int(round(dil*size/caph*capheight*0+dil*caph/capheight))  # dil given in output px
        if k>0: a=cv2.dilate(a,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*k+1,2*k+1)))
    sc=capheight/caph
    c=np.cos(np.radians(ang)); s=np.sin(np.radians(ang))
    # glyph coords (u,v) relative to centre -> image
    ux=(x0+x1)/2; uy=(yt+yb)/2
    A=np.array([[c*sc*stretch,-s*sc],[s*sc*stretch,c*sc]])
    t=np.array([cx,cy])-A@np.array([ux,uy])
    M=np.c_[A,t]
    return cv2.warpAffine(a,M,(shape[1],shape[0]),flags=cv2.INTER_AREA if sc<0.5 else cv2.INTER_LINEAR)
def ncc(a,b,mask=None):
    if mask is not None: a=a[mask]; b=b[mask]
    a=a-a.mean(); b=b-b.mean()
    return float((a*b).sum()/np.sqrt((a*a).sum()*(b*b).sum()+1e-9))
def fit(img,text,family,style,init,blur=1.5,tracking=0.0,rng=(8,8,3,0.12),iters=3,dil=0,stretch=1.0,fit_stretch=False,verbose=False):
    """img float 0..1. init=(cx,cy,ang,cap). coordinate search by successive refinement. returns params, score"""
    cx,cy,ang,cap=init
    # work on a crop
    L=len(text)*cap*1.2+80
    x0=int(max(cx-L/2,0)); x1=int(min(cx+L/2,img.shape[1])); y0=int(max(cy-L/2,0)); y1=int(min(cy+L/2,img.shape[0]))
    sub=img[y0:y1,x0:x1]
    p=np.array([cx-x0,cy-y0,ang,cap,stretch],np.float64)
    def score(p):
        t=place(text,family,style,p[0],p[1],p[2],p[3],sub.shape,tracking,stretch=p[4])
        if dil>0: t=cv2.dilate(t,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*dil+1,2*dil+1)))
        t=cv2.GaussianBlur(t,(0,0),blur)
        m=cv2.dilate((t>0.02).astype(np.uint8),np.ones((9,9),np.uint8))>0
        return ncc(t,sub,m)
    steps=np.array([rng[0],rng[1],rng[2],cap*rng[3],0.06 if fit_stretch else 0.0])
    best=score(p)
    for it in range(iters*8):
        improved=False
        for k in range(5):
            if steps[k]==0: continue
            for sgn in (+1,-1):
                q=p.copy(); q[k]+=sgn*steps[k]
                sc=score(q)
                if sc>best+1e-5: best=sc; p=q; improved=True
        if not improved:
            steps*=0.5
            if steps[0]<0.1: break
    return (p[0]+x0,p[1]+y0,p[2],p[3],p[4]),best
