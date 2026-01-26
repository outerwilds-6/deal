# deal/camera_utils.py
import cv2
import time
import os
import config # 导入同级目录下的 config

class SmartCamera:
    """
    智能摄像头类
    根据 config.USE_STATIC_IMAGE 自动决定是打开真实摄像头还是读取图片。
    """
    def __init__(self):
        self.mode = 'static' if config.USE_STATIC_IMAGE else 'real'
        self.cap = None
        self.static_frame = None

        if self.mode == 'static':
            print(f"DEBUG: [SmartCamera] 初始化为【图片模式】，路径: {config.IMG_PATH}", flush=True)
            if not os.path.exists(config.IMG_PATH):
                raise FileNotFoundError(f"找不到图片文件: {config.IMG_PATH}")
            
            # 读取图片
            self.static_frame = cv2.imread(config.IMG_PATH)
            if self.static_frame is None:
                raise ValueError("图片读取失败，可能是格式不支持")
            
            # 缩放过大的图片，防止卡顿
            h, w = self.static_frame.shape[:2]
            if w > 1000:
                scale = 1000 / w
                self.static_frame = cv2.resize(self.static_frame, (0, 0), fx=scale, fy=scale)
                
        else:
            print("DEBUG: [SmartCamera] 初始化为【真实摄像头模式】", flush=True)
            # 强制使用 DSHOW 后端，解决 Windows 兼容性问题
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                raise RuntimeError("无法打开摄像头，请检查设备连接或权限。")

    def read(self):
        """
        模拟 cv2.VideoCapture.read()
        返回: (ret, frame)
        """
        if self.mode == 'static':
            # 模拟一点延迟，防止 CPU 跑满
            time.sleep(0.03)
            # 必须返回副本，否则画图操作会叠加污染原图
            return True, self.static_frame.copy()
        else:
            return self.cap.read()

    def release(self):
        """释放资源"""
        if self.cap:
            self.cap.release()