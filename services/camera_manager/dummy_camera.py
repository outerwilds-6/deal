import cv2
import time
import numpy as np
from typing import Tuple, Optional
from .base import BaseCamera
from .constants import DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS, DUMMY_IMAGE_PATH

class DummyCamera(BaseCamera):
    """
    无摄像头环境下的模拟器
    从指定的 pics 文件夹内加载静态图片作为视频帧输出，便于开发调试
    """
    def __init__(self):
        self._running = False
        self._frame = None

    def start(self) -> None:
        self._running = True
        img = cv2.imread(DUMMY_IMAGE_PATH)

        if img is not None:
            h, w = img.shape[:2]
            scale = min(DEFAULT_WIDTH / w, DEFAULT_HEIGHT / h)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(img, (new_w, new_h))
            canvas = np.zeros((DEFAULT_HEIGHT, DEFAULT_WIDTH, 3), dtype=np.uint8)
            y_off = (DEFAULT_HEIGHT - new_h) // 2
            x_off = (DEFAULT_WIDTH - new_w) // 2
            canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
            self._frame = canvas
        else:
            self._frame = np.zeros((DEFAULT_HEIGHT, DEFAULT_WIDTH, 3), dtype=np.uint8)
            cv2.putText(self._frame, "Dummy Image Not Found!",
                        (50, DEFAULT_HEIGHT // 2), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 0, 255), 2)

    def stop(self) -> None:
        self._running = False

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._running:
            return False, None

        # 模拟真实的摄像头帧率延迟，防止无意义的 CPU 空转
        time.sleep(1.0 / DEFAULT_FPS)
        
        # 返回图像的副本，防止外部意外修改了缓存的原始帧
        return True, self._frame.copy()