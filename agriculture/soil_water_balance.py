"""Daily root-zone bucket model. Units: mm water over the modelled area."""
from dataclasses import dataclass


@dataclass
class SoilState:
    storage_mm: float
    field_capacity_mm: float = 120.0
    wilting_point_mm: float = 35.0


def soil_step(
    state: SoilState,
    eto_mm: float,
    kc: float,
    irrigation_mm: float = 0.0,
    effective_rain_mm: float = 0.0,
    runoff_mm: float = 0.0,
    drainage_mm: float = 0.0,
):
    """Advance root-zone storage while reporting unmet ET when water is insufficient."""
    vals = [eto_mm, kc, irrigation_mm, effective_rain_mm, runoff_mm, drainage_mm]
    if any(v < 0 for v in vals):
        raise ValueError("Water balance inputs must be non-negative")
    if state.field_capacity_mm <= state.wilting_point_mm:
        raise ValueError("Field capacity must exceed wilting point")
    if not state.wilting_point_mm <= state.storage_mm <= state.field_capacity_mm:
        raise ValueError("Initial storage must be between wilting point and field capacity")

    etc = eto_mm * kc
    water_before_et = (
        state.storage_mm + irrigation_mm + effective_rain_mm - runoff_mm - drainage_mm
    )
    overflow = max(0.0, water_before_et - state.field_capacity_mm)
    available = min(state.field_capacity_mm, water_before_et)

    # Water below wilting point is unavailable to the crop in this bucket approximation.
    available_above_wilt = max(0.0, available - state.wilting_point_mm)
    actual_et = min(etc, available_above_wilt)
    unmet_et = max(0.0, etc - actual_et)
    storage = max(state.wilting_point_mm, available - actual_et)

    residual = (
        state.storage_mm
        + irrigation_mm
        + effective_rain_mm
        - runoff_mm
        - drainage_mm
        - overflow
        - actual_et
        - storage
    )
    deficit = max(0.0, state.field_capacity_mm - storage)
    stress = max(
        0.0,
        min(
            1.0,
            (state.wilting_point_mm + 0.5 * (state.field_capacity_mm - state.wilting_point_mm) - storage)
            / max(1.0, 0.5 * (state.field_capacity_mm - state.wilting_point_mm)),
        ),
    )
    return {
        "etc_mm": etc,
        "actual_et_mm": actual_et,
        "unmet_et_mm": unmet_et,
        "storage_mm": storage,
        "deficit_mm": deficit,
        "overflow_mm": overflow,
        "stress_index": stress,
        "balance_residual_mm": residual,
    }


def irrigation_requirement_mm(state: SoilState, target_fraction: float = 0.75, efficiency: float = 0.9):
    if not 0 < target_fraction <= 1 or not 0 < efficiency <= 1:
        raise ValueError("Fractions must be in (0, 1]")
    target = state.wilting_point_mm + target_fraction * (
        state.field_capacity_mm - state.wilting_point_mm
    )
    net = max(0.0, target - state.storage_mm)
    return net / efficiency
