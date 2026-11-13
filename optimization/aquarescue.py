"""Transparent water allocation heuristics with feasibility reporting."""
def allocate_water(demands, available_l, priorities=None, strategy="stress_minimization"):
    if available_l < 0 or any(d < 0 for d in demands): raise ValueError("Water and demand must be non-negative")
    n=len(demands); priorities=priorities or [1.0]*n
    if len(priorities)!=n: raise ValueError("Priority count must match demand count")
    total=sum(demands)
    if total <= available_l: alloc=list(demands)
    elif strategy=="equal_proportional":
        scale=available_l/total if total else 0; alloc=[d*scale for d in demands]
    else:
        # Weighted progressive allocation: larger priority receives a larger share.
        weights=[max(0.01,p) for p in priorities]
        alloc=[0.0]*n; remaining=available_l; active=set(range(n))
        while remaining>1e-9 and active:
            weight_sum=sum(weights[i] for i in active)
            proposed={i:remaining*weights[i]/weight_sum for i in active}
            saturated=[i for i in active if alloc[i]+proposed[i]>=demands[i]]
            if not saturated:
                for i,v in proposed.items(): alloc[i]+=v
                remaining=0
            else:
                for i in saturated:
                    take=demands[i]-alloc[i]; alloc[i]+=take; remaining-=take; active.remove(i)
    unmet=[max(0,d-a) for d,a in zip(demands,alloc)]
    return {"allocation_l":alloc,"unmet_l":unmet,"requested_l":total,"allocated_l":sum(alloc),"shortage_l":max(0,total-sum(alloc)),"feasible":total<=available_l+1e-8}
