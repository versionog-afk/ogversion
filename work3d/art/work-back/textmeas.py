# Edge-based measurement of a (near horizontal) single-line text block: length L, cap height h.
import cv2, numpy as np
def measure(img, thr=None, exclude_tops=True, debug=None):
    """img float (text bright). returns L, h, angle_deg.  Text assumed roughly horizontal.
    L: from leftmost ink to rightmost ink along baseline direction; h: distance between robust top and bottom edge lines."""
    a=img.astype(np.float32)
    if thr is None:
        hi=np.percentile(a,99.5); lo=np.percentile(a,20); thr=(hi+lo)/2
    b=a>thr
    H,W=b.shape
    cols=np.nonzero(b.any(0))[0]
    xs=[];tops=[];bots=[]
    for x in cols:
        col=a[:,x]; ys=np.nonzero(col>thr)[0]
        y0=ys[0]; y1=ys[-1]
        # subpixel crossing
        t=y0-(col[y0]-thr)/(col[y0]-col[y0-1]+1e-6) if y0>0 else y0
        bt=y1+(col[y1]-thr)/(col[y1]-col[y1+1]+1e-6) if y1<H-1 else y1
        xs.append(x);tops.append(t);bots.append(bt)
    xs=np.array(xs,float);tops=np.array(tops);bots=np.array(bots)
    def robust_line(x,y,side):
        # iterative: fit line, keep points close to the line on the "flat" side
        sel=np.ones(len(x),bool)
        for it in range(8):
            p=np.polyfit(x[sel],y[sel],1); r=y-np.polyval(p,x)
            # for tops: flat letter tops are the *lowest y*... carons go higher (smaller y) ; many columns (inside A, gaps) have larger y.
            if side=='top': q=np.percentile(r[sel],25); sel=np.abs(r-q)<max(0.6,0.15*np.std(r[sel]))
            else: q=np.percentile(r[sel],75); sel=np.abs(r-q)<max(0.6,0.15*np.std(r[sel]))
            if sel.sum()<10: break
        p=np.polyfit(x[sel],y[sel],1)
        return p,sel
    pt,st=robust_line(xs,tops,'top'); pb,sb=robust_line(xs,bots,'bot')
    slope=(pt[0]+pb[0])/2; ang=np.degrees(np.arctan(slope))
    xm=xs.mean()
    h=(np.polyval(pb,xm)-np.polyval(pt,xm))*np.cos(np.arctan(slope))
    # length along baseline dir: project ink pixels (subpixel left/right edges) on direction
    ys_,xs_=np.nonzero(b)
    # restrict to rows between the top and bottom lines (exclude caron/comma tail)
    yt=np.polyval(pt,xs_); yb=np.polyval(pb,xs_)
    keep=(ys_>=yt-0.5)&(ys_<=yb+0.5)
    xs_=xs_[keep]; ys_=ys_[keep]
    u=np.cos(np.arctan(slope)); v=np.sin(np.arctan(slope))
    # subpixel horizontal edges: for the extreme rows use row profiles
    def edge_left():
        best=1e9
        for y in range(int(np.polyval(pt,xs.min())+2),int(np.polyval(pb,xs.min())-1)):
            row=a[y]; idx=np.nonzero(row>thr)[0]
            if len(idx)==0: continue
            x0=idx[0]; xe=x0-(row[x0]-thr)/(row[x0]-row[x0-1]+1e-6) if x0>0 else x0
            best=min(best,xe*u+y*v)
        return best
    def edge_right():
        best=-1e9
        for y in range(int(np.polyval(pt,xs.max())+2),int(np.polyval(pb,xs.max())-1)):
            row=a[y]; idx=np.nonzero(row>thr)[0]
            if len(idx)==0: continue
            x1=idx[-1]; xe=x1+(row[x1]-thr)/(row[x1]-row[x1+1]+1e-6) if x1<W-1 else x1
            best=max(best,xe*u+y*v)
        return best
    L=edge_right()-edge_left()
    if debug:
        vis=cv2.cvtColor((np.clip(a/a.max(),0,1)*255).astype(np.uint8),cv2.COLOR_GRAY2BGR)
        vis=cv2.resize(vis,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
        for p,c in ((pt,(0,0,255)),(pb,(0,255,0))):
            cv2.line(vis,(0,int(3*np.polyval(p,0))),(3*W,int(3*np.polyval(p,W))),c,1)
        cv2.imwrite(debug,vis)
    return L,h,ang
