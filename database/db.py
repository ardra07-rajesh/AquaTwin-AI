"""SQLite persistence for farm configuration, plans, weather and field records."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, String, Float, Integer, DateTime, ForeignKey, JSON, Text, desc
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config.settings import DB_PATH


class Base(DeclarativeBase):
    pass


class FarmRecord(Base):
    __tablename__ = "farms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(120), default="Not specified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ZoneRecord(Base):
    __tablename__ = "zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"))
    zone_code: Mapped[str] = mapped_column(String(20))
    crop: Mapped[str] = mapped_column(String(40))
    method: Mapped[str] = mapped_column(String(20))
    area_m2: Mapped[float] = mapped_column(Float)
    tier: Mapped[int] = mapped_column(Integer, default=1)
    plant_count: Mapped[int] = mapped_column(Integer, default=0)


class RunRecord(Base):
    __tablename__ = "simulation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"))
    scenario: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    inputs: Mapped[dict] = mapped_column(JSON)
    outputs: Mapped[dict] = mapped_column(JSON)


class ConfigurationRecord(Base):
    __tablename__ = "configuration_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"))
    config_type: Mapped[str] = mapped_column(String(60), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    payload: Mapped[dict] = mapped_column(JSON)


class ActualIrrigationRecord(Base):
    __tablename__ = "actual_irrigation_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("simulation_runs.id"), nullable=True)
    zone_code: Mapped[str] = mapped_column(String(20), index=True)
    actual_water_l: Mapped[float] = mapped_column(Float)
    runtime_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(30), default="manual entry")


class WeatherRecord(Base):
    __tablename__ = "weather_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"))
    source: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    timezone_name: Mapped[str] = mapped_column(String(80), default="Local timezone")
    payload: Mapped[dict] = mapped_column(JSON)


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create any missing tables. Existing v10 tables are left intact."""
    Base.metadata.create_all(engine)


def _farm(session, name: str = "AquaTwin Demonstration Farm", location: str = "Not specified") -> FarmRecord:
    farm = session.query(FarmRecord).order_by(FarmRecord.id).first()
    if farm is None:
        farm = FarmRecord(name=name[:120], location=location[:120])
        session.add(farm)
        session.flush()
    else:
        if name and name != "AquaTwin Demonstration Farm":
            farm.name = name[:120]
        if location and location != "Not specified":
            farm.location = location[:120]
    return farm


def save_run(scenario: str, inputs: dict, outputs: dict, farm_name: str = "AquaTwin Demonstration Farm", location: str = "Not specified") -> int:
    init_db()
    with SessionLocal() as session:
        farm = _farm(session, farm_name, location)
        record = RunRecord(farm_id=farm.id, scenario=scenario[:80], inputs=inputs, outputs=outputs)
        session.add(record)
        session.commit()
        return int(record.id)


def save_configuration(config_type: str, payload: dict, farm_name: str = "AquaTwin Demonstration Farm", location: str = "Not specified") -> int:
    init_db()
    with SessionLocal() as session:
        farm = _farm(session, farm_name, location)
        record = ConfigurationRecord(farm_id=farm.id, config_type=config_type[:60], payload=payload)
        session.add(record)
        session.commit()
        return int(record.id)


def load_latest_configuration(config_type: str) -> dict | None:
    init_db()
    with SessionLocal() as session:
        record = session.query(ConfigurationRecord).filter_by(config_type=config_type).order_by(desc(ConfigurationRecord.created_at), desc(ConfigurationRecord.id)).first()
        return dict(record.payload) if record else None


def save_actual_irrigation(zone_code: str, actual_water_l: float, plan_id: int | None = None, runtime_min: float | None = None, notes: str = "", farm_name: str = "AquaTwin Demonstration Farm", location: str = "Not specified") -> int:
    if actual_water_l < 0 or (runtime_min is not None and runtime_min < 0):
        raise ValueError("Actual water and runtime must be non-negative.")
    init_db()
    with SessionLocal() as session:
        farm = _farm(session, farm_name, location)
        record = ActualIrrigationRecord(
            farm_id=farm.id, plan_id=plan_id, zone_code=zone_code[:20],
            actual_water_l=float(actual_water_l), runtime_min=None if runtime_min is None else float(runtime_min),
            notes=notes, source="manual entry",
        )
        session.add(record)
        session.commit()
        return int(record.id)


def save_weather(latitude: float, longitude: float, timezone_name: str, payload: dict, farm_name: str = "AquaTwin Demonstration Farm", location: str = "Not specified") -> int:
    init_db()
    with SessionLocal() as session:
        farm = _farm(session, farm_name, location)
        record = WeatherRecord(
            farm_id=farm.id, source="Open-Meteo forecast", latitude=float(latitude),
            longitude=float(longitude), timezone_name=timezone_name[:80], payload=payload,
        )
        session.add(record)
        session.commit()
        return int(record.id)


def list_runs(limit: int = 250) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        records = session.query(RunRecord).order_by(desc(RunRecord.created_at), desc(RunRecord.id)).limit(limit).all()
        return [{"id": r.id, "scenario": r.scenario, "created_at": r.created_at.isoformat() if r.created_at else "", "inputs": r.inputs or {}, "outputs": r.outputs or {}} for r in records]


def list_actual_irrigation(limit: int = 500) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        records = session.query(ActualIrrigationRecord).order_by(desc(ActualIrrigationRecord.recorded_at), desc(ActualIrrigationRecord.id)).limit(limit).all()
        return [{"id": r.id, "plan_id": r.plan_id, "zone": r.zone_code, "actual_water_l": r.actual_water_l, "runtime_min": r.runtime_min, "recorded_at": r.recorded_at.isoformat() if r.recorded_at else "", "notes": r.notes, "source": r.source} for r in records]


def list_weather_records(limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        records = session.query(WeatherRecord).order_by(desc(WeatherRecord.fetched_at), desc(WeatherRecord.id)).limit(limit).all()
        return [{"id": r.id, "source": r.source, "latitude": r.latitude, "longitude": r.longitude, "fetched_at": r.fetched_at.isoformat() if r.fetched_at else "", "timezone": r.timezone_name, "payload": r.payload or {}} for r in records]
