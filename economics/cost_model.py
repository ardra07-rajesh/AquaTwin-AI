def estimate_cost(water_l, energy_kwh, water_price_per_l=0.02, electricity_price_per_kwh=8.0):
    return {"water_cost":water_l*water_price_per_l,"energy_cost":energy_kwh*electricity_price_per_kwh,"total_cost":water_l*water_price_per_l+energy_kwh*electricity_price_per_kwh}
