import cv2, numpy as np, os
ROOT='work3d/'   # run from the repository root
SRC=ROOT+'ref/'
W=ROOT+'art/work-back/'
K=7                      # work scale: mock px -> work px
MW,MH=238,264            # mock crop size (x 762..1000, y 181..445 of mockup-sheet, grey shirt)
def mock_ref():
    m=cv2.imread(SRC+'mockup-sheet.jpg',0).astype(np.float32)
    g=255-m[181:445,762:1000]; g=(g-16)/(255-16)
    b=m[759:759+264,762:1000]/255.
    r=np.clip((g+b)/2,0,1)
    return r
def frame(i):
    return cv2.imread(SRC+'all/a_%04d.png'%i)
def frame_ink(i):
    """returns gray float 0..1 ink intensity (shirt-masked), and the map-only mask bbox"""
    im=frame(i); g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
    dark=(g<75).astype(np.uint8)
    cl=cv2.morphologyEx(dark,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(41,41)))
    n,lab,st,cen=cv2.connectedComponentsWithStats(cl)
    k=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); shirt=(lab==k).astype(np.uint8)
    shirt=cv2.erode(shirt,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15)))
    ink=((g>125)&(shirt>0)).astype(np.uint8)
    n,lab,st,cen=cv2.connectedComponentsWithStats(ink,connectivity=8)
    k=1+np.argmax(st[1:,cv2.CC_STAT_AREA])
    x,y,w,h=st[k,:4]
    return g,shirt,ink,(x,y,w,h),lab,st,cen
