"""Generate transparent candidate schedules and Pareto non-dominated set."""
def candidate_schedules(demands, available_l, energy_per_l=0.015, cost_per_l=0.02, priorities=None):
    from .aquarescue import allocate_water
    priorities=priorities or [1.0]*len(demands)
    candidates=[]
    for strategy in ["equal_proportional","stress_minimization"]:
        r=allocate_water(demands,available_l,priorities,strategy)
        water=r["allocated_l"]; energy=water*energy_per_l; cost=water*cost_per_l
        stress=sum(u*p for u,p in zip(r["unmet_l"],priorities))
        candidates.append({"strategy":strategy,"water_l":water,"energy_kwh":energy,"cost":cost,"stress_penalty":stress,"shortage_l":r["shortage_l"],"allocation_l":r["allocation_l"]})
    # Pareto filtering across minimized metrics.
    for c in candidates:
        c["pareto"] = not any(all(o[k] <= c[k] for k in ["water_l","energy_kwh","cost","stress_penalty"]) and any(o[k] < c[k] for k in ["water_l","energy_kwh","cost","stress_penalty"]) for o in candidates if o is not c)
    return candidates
