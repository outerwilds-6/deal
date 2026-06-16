import cv2
import logging
import threading
import time
from typing import Tuple, Optional
import numpy as np
from .base import BaseCamera
from .constants import DEFAULT_CAMERA_ID, DEFAULT_WIDTH, DEFAULT_HEIGHT

logger = logging.getLogger(__name__)

CAMERA_RETRY_MAX = 3
CAMERA_RETRY_DELAY = 1.0


class RealCamera(BaseCamera):
    def __init__(self, camera_id: int = DEFAULT_CAMERA_ID):
        super().__init__()
        self.camera_id = camera_id
        self.cap = None

        self._frame = None
        self._ret = False
        self._running = False
        self._lock = threading.Lock()
        self._thread = None

    def start(self) -> None:
        if self._running:
            return

        last_error = None
        for attempt in range(1, CAMERA_RETRY_MAX + 1):
            logger.info(f"正在打开摄像头 (ID={self.camera_id}) ... 第 {attempt}/{CAMERA_RETRY_MAX} 次尝试")

            self.cap = cv2.VideoCapture(self.camera_id)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
                actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logger.info(
                    f"摄像头已打开 (ID={self.camera_id}), "
                    f"分辨率: {int(actual_w)}x{int(actual_h)}, "
                    f"后端: {self.cap.getBackendName()}"
                )
                self._running = True
                self._thread = threading.Thread(target=self._update, daemon=True)
                self._thread.start()
                return
            else:
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                last_error = f"无法打开摄像头 ID={self.camera_id}"
                logger.warning(
                    f"摄像头打开失败 (ID={self.camera_id}) "
                    f"— 第 {attempt}/{CAMERA_RETRY_MAX} 次尝试"
                )
                if attempt < CAMERA_RETRY_MAX:
                    logger.info(f"等待 {CAMERA_RETRY_DELAY:.0f}s 后重试...")
                    time.sleep(CAMERA_RETRY_DELAY)

        raise RuntimeError(f"{last_error} (已重试 {CAMERA_RETRY_MAX} 次)")

    def _update(self) -> None:
        while self._running:
            ret, frame = self.cap.read()
            with self._lock:
                self._ret = ret
                if ret:
                    self._frame = frame

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if self._ret and self._frame is not None:
                frame = self._frame.copy()
                frame = self._blend_qr(frame)
                return True, frame
            return False, None

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self.cap is not None:
            self.cap.release()
