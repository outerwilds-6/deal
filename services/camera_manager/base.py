from abc import ABC, abstractmethod
from typing import Tuple, Optional
import cv2
import numpy as np
from .constants import OVERLAY_QR_WIDTH_RATIO, OVERLAY_BOTTOM_MARGIN


class BaseCamera(ABC):
    """摄像头的抽象基类"""

    def __init__(self):
        self._overlay_qr: Optional[np.ndarray] = None

    @abstractmethod
    def start(self) -> None:
        """初始化摄像头并启动视频流获取（例如启动后台线程）"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止视频流获取并释放资源"""
        pass

    @abstractmethod
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        获取最新的一帧
        :return: (是否成功读取, BGR格式的图像矩阵)
        """
        pass

    def set_overlay_qr(self, qr_image: Optional[np.ndarray]) -> None:
        """设置或清除演示用 QR 叠加图像。传入 None 则清除叠加。"""
        self._overlay_qr = qr_image

    def _blend_qr(self, frame: np.ndarray) -> np.ndarray:
        """将已设置的 QR 叠加图像以 alpha 混合方式画到帧的下半区域（全 uint8 零临时放大）"""
        if self._overlay_qr is None:
            return frame

        h, w = frame.shape[:2]
        qh, qw = self._overlay_qr.shape[:2]

        target_w = int(w * OVERLAY_QR_WIDTH_RATIO)
        scale = target_w / qw
        target_h = int(qh * scale)

        qr_resized = cv2.resize(self._overlay_qr, (target_w, target_h))

        x = (w - target_w) // 2
        y = h - target_h - OVERLAY_BOTTOM_MARGIN

        x = max(0, min(x, w - target_w))
        y = max(0, min(y, h - target_h))

        roi = frame[y:y + target_h, x:x + target_w]
        blended = cv2.addWeighted(qr_resized, 0.78, roi, 0.22, 0)
        frame[y:y + target_h, x:x + target_w] = blended
        return frame
