import os
import onnxruntime

# ================= 核心开关 =================
USE_STATIC_IMAGE = True  
IMAGE_FILENAME = "test_face.png"

# ================= 参数设置 =================
SIMILARITY_THRESHOLD = 0.5
DEFAULT_REGISTER_ID = "abc"
DET_SIZE = (640, 640)

# 【新增】AI 检测的时间间隔 (秒)
# 0.5 表示每秒只识别 2 次，大大降低 CPU 占用
# 如果你有强力 GPU，可以设为 0.1 或 0
INFERENCE_INTERVAL = 0.5 

# ================= 路径配置 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "faces.db")
LOG_DB_PATH = os.path.join(BASE_DIR, "access_log.db") # 补上这个常用的
IMG_PATH = os.path.join(BASE_DIR, IMAGE_FILENAME)
MODEL_NAME = 'buffalo_l'

# ================= GPU 配置 =================

PROVIDERS = ['CUDAExecutionProvider', 'CPUExecutionProvider']

# 打印一下确认 config 被加载时检测到了什么
print(f"DEBUG: Config 加载中，可用设备: {onnxruntime.get_available_providers()}", flush=True)