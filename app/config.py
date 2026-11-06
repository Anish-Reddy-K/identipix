import os
from pathlib import Path

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(Path(__file__).resolve().parent.parent / "models")))
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.40"))  # lowest score shown ("might be you")
STRONG_THRESHOLD = float(os.getenv("STRONG_THRESHOLD", "0.43"))  # at or above: "found you"
DETECT_SCORE = float(os.getenv("DETECT_SCORE", "0.8"))
MIN_FACE_PX = int(os.getenv("MIN_FACE_PX", "24"))
INDEX_LONG_SIDE = int(os.getenv("INDEX_LONG_SIDE", "1600"))
INDEX_WORKERS = int(os.getenv("INDEX_WORKERS", "8"))
MAX_CONCURRENT_EVENTS = int(os.getenv("MAX_CONCURRENT_EVENTS", "2"))
SYNC_INTERVAL_MIN = int(os.getenv("SYNC_INTERVAL_MIN", "10"))
MATCH_RATE_PER_MIN = int(os.getenv("MATCH_RATE_PER_MIN", "10"))
CREATE_RATE_PER_HOUR = int(os.getenv("CREATE_RATE_PER_HOUR", "5"))
