# deal/config.py
import os

# ================= 核心开关 =================
# True = 使用静态图片模拟摄像头
# False = 使用真实摄像头
USE_STATIC_IMAGE = True 

# 模拟摄像头使用的图片文件名
IMAGE_FILENAME = "test_face.png"

# ================= 参数设置 =================
# 人脸识别阈值 (0.5 通常是一个平衡点)
SIMILARITY_THRESHOLD = 0.5

# 默认注册时的 ID (录入脚本目前使用固定 ID，你可以以后改成 input 输入)
DEFAULT_REGISTER_ID = "abc"

# 摄像头窗口分辨率 (仅用于 FaceAnalysis 初始化参数)
DET_SIZE = (640, 640)

# ================= 路径配置 (自动计算) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库路径
DB_PATH = os.path.join(BASE_DIR, "faces.db")

# 图片路径
IMG_PATH = os.path.join(BASE_DIR, IMAGE_FILENAME)

# 模型名称
MODEL_NAME = 'buffalo_l'