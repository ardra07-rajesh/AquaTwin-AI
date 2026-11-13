from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database.db as db


def use_temp_database(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test_aquatwin.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    db.init_db()


def test_configuration_plan_and_actual_records_persist(monkeypatch, tmp_path):
    use_temp_database(monkeypatch, tmp_path)
    config_id = db.save_configuration("farm_configuration", {"zones": [{"zone": "Z01"}]}, "Farm A", "Test location")
    assert config_id > 0
    assert db.load_latest_configuration("farm_configuration")["zones"][0]["zone"] == "Z01"

    plan_id = db.save_run("Planned irrigation", {"water_l": 100}, {"zone_rows": [{"Zone": "Z01", "Allocation (L)": 80}]}, "Farm A", "Test location")
    assert plan_id > 0
    assert db.list_runs()[0]["outputs"]["zone_rows"][0]["Allocation (L)"] == 80

    actual_id = db.save_actual_irrigation("Z01", 75, plan_id, 12.5, "Flow meter noted manually", "Farm A", "Test location")
    records = db.list_actual_irrigation()
    assert actual_id > 0
    assert records[0]["actual_water_l"] == 75
    assert records[0]["plan_id"] == plan_id


def test_negative_actual_water_rejected(monkeypatch, tmp_path):
    use_temp_database(monkeypatch, tmp_path)
    import pytest
    with pytest.raises(ValueError):
        db.save_actual_irrigation("Z01", -1)


def test_weather_fetch_payload_is_retained_with_timestamp(monkeypatch, tmp_path):
    use_temp_database(monkeypatch, tmp_path)
    record_id = db.save_weather(12.9, 77.5, "Asia/Kolkata", {"current": {"temperature_2m": 28.2}, "daily": []})
    records = db.list_weather_records()
    assert record_id > 0
    assert records[0]["latitude"] == 12.9
    assert records[0]["timezone"] == "Asia/Kolkata"
    assert records[0]["payload"]["current"]["temperature_2m"] == 28.2
    assert records[0]["fetched_at"]
