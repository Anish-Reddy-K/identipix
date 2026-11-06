FROM python:3.12-slim

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" opencv-python-headless numpy httpx python-multipart segno

WORKDIR /app
RUN mkdir -p /app/models && chmod 755 /app/models
ADD --chmod=644 https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx /app/models/
ADD --chmod=644 https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx /app/models/
RUN for f in /app/models/*.onnx; do [ "$(stat -c %s "$f")" -gt 102400 ] || { echo "model too small: $f"; exit 1; }; done

COPY app /app/app
RUN useradd -m appuser && mkdir /data && chown appuser /data
USER appuser
# fail the build if the app user cannot load the models (a permission bug once shipped silently)
RUN python -c "import cv2; cv2.FaceDetectorYN.create('/app/models/face_detection_yunet_2023mar.onnx','',(320,320)); cv2.FaceRecognizerSF.create('/app/models/face_recognition_sface_2021dec.onnx','')"
ENV DATA_DIR=/data MODELS_DIR=/app/models
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
