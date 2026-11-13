"""Water and dissolved-nutrient mass balance for a simplified recirculating system.

All water flows use litres per simulation step. Nutrient masses use grams.
EC and pH remain observed inputs; this simplified mass balance does not infer
EC from total dissolved nutrient mass because ion composition is not modelled.
"""
from dataclasses import dataclass


@dataclass
class HydroState:
    volume_l: float
    nutrient_mass_g: float = 0.0


def hydro_step(
    state: HydroState,
    makeup_l=0.0,
    return_l=0.0,
    uptake_l=0.0,
    purge_l=0.0,
    loss_l=0.0,
    nutrient_added_g=0.0,
    nutrient_uptake_g=0.0,
    nutrient_loss_g=0.0,
):
    """Advance reservoir water and nutrient inventories by one time step."""
    flows = [makeup_l, return_l, uptake_l, purge_l, loss_l]
    masses = [nutrient_added_g, nutrient_uptake_g, nutrient_loss_g]
    if state.volume_l <= 0:
        raise ValueError("Initial reservoir volume must be positive")
    if state.nutrient_mass_g < 0:
        raise ValueError("Initial nutrient mass must be non-negative")
    if any(v < 0 for v in flows + masses):
        raise ValueError("Hydroponic flows and masses must be non-negative")

    next_volume = state.volume_l + makeup_l + return_l - uptake_l - purge_l - loss_l
    if next_volume <= 0:
        raise ValueError("Reservoir volume must remain positive")

    # Purge and leakage remove solution at the starting reservoir concentration.
    starting_concentration = state.nutrient_mass_g / state.volume_l
    dissolved_mass_removed = (purge_l + loss_l) * starting_concentration
    next_mass = (
        state.nutrient_mass_g
        + nutrient_added_g
        - nutrient_uptake_g
        - nutrient_loss_g
        - dissolved_mass_removed
    )
    if next_mass < -1e-9:
        raise ValueError("Nutrient removal exceeds the available dissolved nutrient mass")
    next_mass = max(0.0, next_mass)

    return {
        "volume_l": next_volume,
        "nutrient_mass_g": next_mass,
        "concentration_g_l": next_mass / next_volume,
        "nutrient_removed_by_purge_g": dissolved_mass_removed,
        "water_residual_l": (
            state.volume_l + makeup_l + return_l - uptake_l - purge_l - loss_l - next_volume
        ),
    }


def ec_status(ec_ms_cm, low=1.2, high=2.6):
    """Classify an observed EC against the selected demo operating band."""
    if ec_ms_cm < low:
        return "Below configured range"
    if ec_ms_cm > high:
        return "Above configured range"
    return "Within configured range"
