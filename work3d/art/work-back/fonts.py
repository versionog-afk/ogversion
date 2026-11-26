import json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
FJ='work3d/fonts/fonts.json'
IDX=json.load(open(FJ))
def fpath(family,style):
    for e in IDX:
        if e['family']==family and e['style']==style: return e['path']
    raise KeyError((family,style))
def render(text,family,style,size=100,pad=20,tracking=0.0):
    f=ImageFont.truetype(fpath(family,style),size)
    if tracking==0:
        l,t,r,b=f.getbbox(text)
        im=Image.new('L',(r-l+2*pad,b-t+2*pad),0); d=ImageDraw.Draw(im); d.text((pad-l,pad-t),text,font=f,fill=255)
        return np.array(im)
    # manual tracking (em fraction)
    x=0; W=int(sum(f.getlength(c)+tracking*size for c in text))+2*pad+size
    asc,desc=f.getmetrics(); im=Image.new('L',(W,asc+desc+2*pad+size//2),0); d=ImageDraw.Draw(im)
    for c in text:
        d.text((pad+x,pad+size//4),c,font=f,fill=255); x+=f.getlength(c)+tracking*size
    a=np.array(im); ys,xs=np.nonzero(a>0)
    return a[max(ys.min()-pad,0):ys.max()+pad,max(xs.min()-pad,0):xs.max()+pad]
