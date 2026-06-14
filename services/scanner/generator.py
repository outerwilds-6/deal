import json
import numpy as np
import qrcode
from services.scanner.constants import (
    DEFAULT_QR_VERSION, DEFAULT_BOX_SIZE,
    DEFAULT_BORDER, DEFAULT_SAVE_PATH
)


def _encode_parcel_data(parcel_data: dict) -> str:
    data_to_encode = {k: v for k, v in parcel_data.items() if k != "parcel_id"}
    return json.dumps(data_to_encode, ensure_ascii=False, separators=(',', ':'))


def _make_qr(parcel_data: dict):
    json_str = _encode_parcel_data(parcel_data)
    qr = qrcode.QRCode(
        version=DEFAULT_QR_VERSION,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=DEFAULT_BOX_SIZE,
        border=DEFAULT_BORDER
    )
    qr.add_data(json_str)
    qr.make(fit=True)
    return qr


def generate_qr(parcel_data: dict, filename: str = DEFAULT_SAVE_PATH) -> bool:
    """
    将包裹信息生成二维码图片
    :param parcel_data: 包含包裹信息的字典
    :param filename: 保存的文件路径
    :return: 成功返回 True
    """
    try:
        qr = _make_qr(parcel_data)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        return True
    except Exception as e:
        print(f"QR Generate Error: {e}")
        return False


def generate_qr_image(parcel_data: dict) -> np.ndarray:
    """
    将包裹信息生成二维码图片，返回 BGR 格式的 numpy 数组 (OpenCV 可用)
    :param parcel_data: 包含包裹信息的字典
    :return: BGR 格式的 uint8 数组
    """
    qr = _make_qr(parcel_data)
    img = qr.make_image(fill_color="black", back_color="white")
    rgb = np.array(img.convert("RGB"), dtype=np.uint8)
    bgr = rgb[:, :, ::-1].copy()
    return bgr