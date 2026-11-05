FROM python:3.12-slim

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" opencv-python-headless numpy httpx python-multipart segno

WORKDIR /app
ADD --chmod=644 https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx /app/models/
ADD --chmod=644 https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx /app/models/
RUN for f in /app/models/*.onnx; do [ "$(stat -c %s "$f")" -gt 102400 ] || { echo "model too small: $f"; exit 1; }; done

COPY app /app/app
RUN useradd -m appuser && mkdir /data && chown appuser /data
USER appuser
ENV DATA_DIR=/data MODELS_DIR=/app/models
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
