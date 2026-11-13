import pytest
from agriculture.decision_engine import allocate, build_schedule, estimate_zone_demand

def test_allocation_respects_supply_and_demand():
    r=allocate([100,200,300],250,[1,2,3],'Priority protection')
    assert sum(r['allocation_l']) == pytest.approx(250)
    assert all(a <= d + 1e-8 for a,d in zip(r['allocation_l'],[100,200,300]))
    assert r['shortage_l'] == pytest.approx(350)

def test_proportional_allocation():
    r=allocate([100,300],200,[1,1],'Proportional sharing')
    assert r['allocation_l'] == pytest.approx([50,150])

def test_sufficient_water_covers_demand():
    r=allocate([10,20],100,[1,1])
    assert r['allocation_l'] == [10,20]
    assert r['shortage_l'] == 0

def test_demand_is_positive_for_dry_soil():
    litres, mm=estimate_zone_demand('Tomato',20,20,30,50,8,'Flowering',.9)
    assert litres > 0 and mm > 0

def test_hydroponic_topup_responds_to_reservoir_level():
    low,_=estimate_zone_demand('Basil',10,60,28,60,7,'Vegetative',.9,'Hydroponic',100,500,100)
    high,_=estimate_zone_demand('Basil',10,60,28,60,7,'Vegetative',.9,'Hydroponic',400,500,100)
    assert low > high

def test_schedule_runtime_and_cost():
    rows=build_schedule([{'zone':'A','crop':'Tomato'}],[120],24,1,8,20)
    assert rows[0]['Duration (min)'] == 5
    assert rows[0]['Energy (kWh)'] == pytest.approx(5/60)

@pytest.mark.parametrize('demands,water', [([-1],10),([1],-1)])
def test_negative_values_rejected(demands,water):
    with pytest.raises(ValueError): allocate(demands,water,[1])

def test_pump_summary_checks_runtime_energy_and_available_window():
    from agriculture.decision_engine import pump_summary

    result = pump_summary(120, 24, 1.2, 8, 0.1)
    assert result["runtime_min"] == pytest.approx(5)
    assert result["energy_kwh"] == pytest.approx(0.1)
    assert result["electricity_cost"] == pytest.approx(0.8)
    assert result["fits_window"] is True

    too_short = pump_summary(120, 24, 1.2, 8, 0.05)
    assert too_short["fits_window"] is False
    assert too_short["overrun_min"] == pytest.approx(2)
