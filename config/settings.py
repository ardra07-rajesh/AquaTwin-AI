from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "aquatwin.db"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)
