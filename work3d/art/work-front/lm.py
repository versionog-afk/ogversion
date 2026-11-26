import numpy as np
def lm(fun,x0,scale=None,iters=200,robust=None,verbose=False,h=1e-6):
    """Levenberg-Marquardt with numerical Jacobian; robust = Huber delta (on residuals) or None."""
    x=np.array(x0,float); n=len(x)
    s=np.ones(n) if scale is None else np.array(scale,float)
    lam=1e-3
    def cost(r):
        if robust is None: return 0.5*np.sum(r*r)
        a=np.abs(r); return np.sum(np.where(a<robust,0.5*r*r,robust*(a-0.5*robust)))
    r=fun(x); c=cost(r)
    for it in range(iters):
        J=np.empty((len(r),n))
        for j in range(n):
            d=np.zeros(n); d[j]=h*s[j]
            J[:,j]=(fun(x+d)-fun(x-d))/(2*h)   # derivative w.r.t. scaled param
        w=np.ones(len(r)) if robust is None else np.where(np.abs(r)<robust,1.0,robust/np.maximum(np.abs(r),1e-30))
        A=J.T@(J*w[:,None]); gvec=J.T@(w*r)
        improved=False
        for _ in range(12):
            try: dx=-np.linalg.solve(A+lam*np.diag(np.diag(A)+1e-12),gvec)
            except np.linalg.LinAlgError: lam*=10; continue
            xn=x+dx*s; rn=fun(xn); cn=cost(rn)
            if cn<c: x,r,c=xn,rn,cn; lam=max(lam/3,1e-9); improved=True; break
            lam*=5
        if verbose: print(it,c)
        if not improved or np.max(np.abs(dx))<1e-10: break
    return x,r
