import cv2
import json
import numpy as np
from typing import Tuple, List
from pyzbar.pyzbar import decode

from services.scanner.constants import (
    BBOX_COLOR, BBOX_THICKNESS, 
    TEXT_COLOR, TEXT_SCALE, TEXT_THICKNESS,
    DEMO_MODE_ENABLED, DEMO_DATA_LIST
)

class QRScanner:
    """
    二维码/条码扫描器
    无状态类，只负责纯粹的图像处理和解码提取
    """
    def __init__(self):
        # 维护演示模式的下标，用于循环提取 DEMO 数据
        self._demo_index = 0
        
    def scan(self, frame: np.ndarray, skip_demo: bool = False) -> Tuple[np.ndarray, List[dict]]:
        """
        扫描帧中的二维码并绘制边框。
        策略：先尝试真实解码（pyzbar），找到结果就直接返回；
        否则若开启演示模式则回退到 Mock 数据。
        :param frame: 原始图像(OpenCV BGR 格式)
        :param skip_demo: 为 True 时跳过演示模式兜底（取件 overlay 场景使用）
        :return: (处理后画框的图像, 提取到的合法字典数据列表)
        """
        annotated_frame = frame.copy()

        # --- 第一阶段：真实解码 ---
        decoded_objects = decode(frame)
        results = []

        for obj in decoded_objects:
            try:
                qr_text = obj.data.decode('utf-8')
                data = json.loads(qr_text)
                if 'tracking_no' in data:
                    results.append(data)
                    (rx, ry, rw, rh) = obj.rect
                    cv2.rectangle(annotated_frame, (rx, ry), (rx + rw, ry + rh),
                                  BBOX_COLOR, BBOX_THICKNESS)
                    cv2.putText(annotated_frame, "DECODED", (rx, ry - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, TEXT_SCALE, TEXT_COLOR, TEXT_THICKNESS)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

        if results:
            return annotated_frame, results

        # --- 第二阶段：演示模式兜底 ---
        if DEMO_MODE_ENABLED and not skip_demo:
            mock_data = DEMO_DATA_LIST[self._demo_index]
            self._demo_index = (self._demo_index + 1) % len(DEMO_DATA_LIST)

            h, w = annotated_frame.shape[:2]
            box_w, box_h = 200, 200
            x, y = (w - box_w) // 2, (h - box_h) // 2

            cv2.rectangle(annotated_frame, (x, y), (x + box_w, y + box_h), BBOX_COLOR, BBOX_THICKNESS)
            cv2.putText(annotated_frame, "DEMO DECODED", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, TEXT_SCALE, TEXT_COLOR, TEXT_THICKNESS)

            return annotated_frame, [mock_data]

        return annotated_frame, []