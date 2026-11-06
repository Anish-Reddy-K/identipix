import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Sample photo with a known face count (a crowd shot from the OpenCV Zoo examples).
# It shows real people, so it is not committed: it is downloaded once into tests/data/ (git-ignored).
SAMPLE = Path(__file__).parent / "data" / "crowd.jpg"
SAMPLE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/example_outputs/largest_selfie.jpg"

if not SAMPLE.exists():
    SAMPLE.parent.mkdir(exist_ok=True)
    try:
        SAMPLE.write_bytes(urllib.request.urlopen(SAMPLE_URL, timeout=30).read())
    except OSError as e:
        print(f"WARNING: could not download the sample image ({e}). Download it to {SAMPLE} to run the face tests.")
