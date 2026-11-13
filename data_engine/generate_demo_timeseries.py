"""Generate explicitly synthetic, multi-zone demonstration observations."""
from pathlib import Path
import numpy as np
import pandas as pd

def generate(days=45, seed=42):
    rng=np.random.default_rng(seed); rows=[]
    for zone,method,crop in [('Z01','soil','Lettuce'),('Z02','soil','Tomato'),('Z03','hydroponic','Lettuce'),('Z04','hydroponic','Basil')]:
        moisture=42.0; reservoir=95.0
        for day in range(days):
            temp=27+4*np.sin(day/6)+rng.normal(0,.7); humidity=62-7*np.sin(day/8)+rng.normal(0,2)
            demand=max(.1,(4.0 if crop=='Lettuce' else 4.5)*(1+.025*(temp-27)))
            if method=='soil':
                moisture=max(15,min(75,moisture-demand*.9+rng.normal(0,.8)))
                rows.append({'day':day+1,'zone_id':zone,'method':method,'crop':crop,'temperature_c':round(temp,2),'humidity_pct':round(humidity,2),'soil_moisture_pct':round(moisture,2),'reservoir_l':None,'estimated_demand_l':round(demand*2.5,2),'source':'synthetic'})
            else:
                reservoir=max(20,min(120,reservoir-demand*.55+rng.normal(0,1)))
                rows.append({'day':day+1,'zone_id':zone,'method':method,'crop':crop,'temperature_c':round(temp,2),'humidity_pct':round(humidity,2),'soil_moisture_pct':None,'reservoir_l':round(reservoir,2),'estimated_demand_l':round(demand*1.8,2),'source':'synthetic'})
    return pd.DataFrame(rows)

if __name__=='__main__':
    out=Path(__file__).resolve().parents[1]/'data/synthetic/multizone_demo_timeseries.csv'; out.parent.mkdir(parents=True,exist_ok=True)
    generate().to_csv(out,index=False); print(f'Wrote {out}')
