# Exhaustive fit of horizontal-ish text: cap height, horizontal stretch, dilation (print gain), angle; translation by matchTemplate
import cv2, numpy as np
from labelfit import place, glyph_img
def gridfit(sub,text,family,style,caps,stretches,dils,angs,blur=1.2,tracking=0.0,pad=14):
    best=(-1,)
    H,W=sub.shape
    for ang in angs:
        for cap in caps:
            for st in stretches:
                # render template tightly
                tw=int(len(text)*cap*0.85*st*(1+tracking)+4*pad); th=int(cap*2.2+2*pad)
                t0=place(text,family,style,tw/2,th/2,ang,cap,(th,tw),tracking,stretch=st)
                for dl in dils:
                    t=t0
                    if dl>0:
                        k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*int(np.ceil(dl))+1,)*2)
                        # fractional dilation: blend
                        td=cv2.dilate(t0,k); fr=dl-np.floor(dl)
                        if fr>0:
                            k2=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*int(np.floor(dl))+1,)*2)
                            t=(1-fr)*cv2.dilate(t0,k2)+fr*td
                        else: t=td
                    t=cv2.GaussianBlur(t,(0,0),blur)
                    ys,xs=np.nonzero(t>0.02)
                    t=t[max(ys.min()-6,0):ys.max()+7,max(xs.min()-6,0):xs.max()+7]
                    if t.shape[0]>=H or t.shape[1]>=W: continue
                    r=cv2.matchTemplate(sub,t.astype(np.float32),cv2.TM_CCOEFF_NORMED)
                    _,mx,_,loc=cv2.minMaxLoc(r)
                    if mx>best[0]: best=(mx,cap,st,dl,ang,loc,t.shape)
    return best
