import cv2
import sqlite3
import numpy as np
from insightface.app import FaceAnalysis
from datetime import datetime
import pytz
import os
import sys
import time

# 引入工具
from camera_utils import SmartCamera
import config

# 防止乱码
sys.stdout.reconfigure(encoding='utf-8')

# === 路径配置 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "faces.db")
LOG_DB_PATH = os.path.join(BASE_DIR, "access_log.db")

# 数据保存目录 (确保生成在 deal 文件夹下)
ENTRANCE_DIR = os.path.join(BASE_DIR, "entrance_data")
IMG_SAVE_DIR = os.path.join(ENTRANCE_DIR, "images")
LABEL_SAVE_DIR = os.path.join(ENTRANCE_DIR, "labels")

os.makedirs(IMG_SAVE_DIR, exist_ok=True)
os.makedirs(LABEL_SAVE_DIR, exist_ok=True)

# 识别特定人脸
print("DEBUG: 加载模型...", flush=True)
app = FaceAnalysis(name=config.MODEL_NAME, providers=config.PROVIDERS)
app.prepare(ctx_id=0, det_size=(640, 640))

# === 使用 SmartCamera ===
try:
    camera = SmartCamera()
except Exception as e:
    print(f"ERROR: 摄像头启动失败: {e}", flush=True)
    sys.exit(1)

# 打开sql
print(f"DEBUG: 连接主数据库: {DB_PATH}", flush=True)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 创建访问日志表
print(f"DEBUG: 连接日志数据库: {LOG_DB_PATH}", flush=True)
log_conn = sqlite3.connect(LOG_DB_PATH)
log_cursor = log_conn.cursor()
log_cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        access_time TIMESTAMP,
        similarity REAL
    )
''')
log_conn.commit()

# 变量初始化
last_result = False
current_result = False
TIME_THRESHOLD = 30  # 单位为秒
last_inference_time = 0      # 【新增】上次检测时间
cached_faces = []            # 【新增】缓存的结果

# 取出所有人的信息
try:
    cursor.execute("SELECT user_id, embedding FROM users")
    rows = cursor.fetchall()
    print(f"DEBUG: 加载了 {len(rows)} 个用户数据", flush=True)
except Exception as e:
    print(f"ERROR: 读取用户数据失败: {e}", flush=True)
    rows = []

# 开始检测
print("DEBUG: 开始检测循环...", flush=True)

while True:
    ret, frame = camera.read()
    if not ret:
        break

    # 【新增】性能优化逻辑 ---------------------------------------
    current_time_clock = time.time()
    
    # 只有当时间间隔超过设定值（例如0.5秒）时，才调用笨重的 app.get()
    if current_time_clock - last_inference_time > config.INFERENCE_INTERVAL:
        cached_faces = app.get(frame)
        last_inference_time = current_time_clock
    
    # 这里的 faces 使用缓存的数据
    faces = cached_faces 
    # -----------------------------------------------------------

    # 每一帧重置最佳匹配 (注意：这里要小心，如果 faces 是缓存的，结果也会延续上一帧的)
    best_user_id = "Unknown"
    best_similarity = -1
    time_diff = 999999 
    last_user_id = None
    
    # 每一帧重置最佳匹配
    best_user_id = "Unknown"
    best_similarity = -1
    time_diff = 999999 # 初始化时间差
    last_user_id = None
    
    faces = app.get(frame)

    # 如果有人脸
    if len(faces) > 0:
        face = faces[0]  # 只取第一张脸
        current_embedding = face.embedding 
        
        # === 核心识别逻辑 ===
        for user_id_db, embedding_bytes in rows:
            registered_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            similarity = np.dot(current_embedding, registered_embedding) / (
                np.linalg.norm(current_embedding) *
                np.linalg.norm(registered_embedding)
            )
            # 记录最相似的人
            if similarity > best_similarity:
                best_similarity = similarity
                best_user_id = user_id_db
        
        # === 判断逻辑 (使用 best_similarity) ===
        if best_similarity > 0.5:
            # 允许通行
            text_1 = "Access Granted"
            color = (0, 255, 0)
            cv2.putText(frame, f"{text_1} ({best_similarity:.2f})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, "You Are", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, f"{best_user_id}", (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            current_result = True
            
            # === 日志检查逻辑 ===
            log_cursor.execute("SELECT user_id, access_time FROM access_log ORDER BY log_id DESC LIMIT 1")
            last_log = log_cursor.fetchone()
            
            # 获取当前时间
            current_time = datetime.now(pytz.timezone("Asia/Shanghai"))
            formatted_time_log = current_time.strftime('%Y-%m-%d %H:%M:%S') # 数据库用
            
            if last_log is None:
                last_user_id = None
                time_diff = 100000 
            else:
                last_user_id, last_access_time_str = last_log
                try:
                    last_access_time_naive = datetime.strptime(last_access_time_str, "%Y-%m-%d %H:%M:%S")
                    last_access_time = pytz.timezone("Asia/Shanghai").localize(last_access_time_naive)
                    time_diff = (current_time - last_access_time).total_seconds()
                except Exception:
                    time_diff = 100000 # 如果时间解析出错，默认允许
        else:
            # 拒绝通行
            text = "Access Denied"
            color = (0, 0, 255)
            cv2.putText(frame, f"{text} ({best_similarity:.2f})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            current_result = False
    else:
        current_result = False

    # === 日志写入与图片保存逻辑 ===
    # 必须满足：当前结果为True，且（状态从False变True OR 换人了 OR 同一个人超过了时间阈值）
    # 注意：这里稍微优化了同事的逻辑：如果一直是 True，也应该根据时间阈值记录，而不是只看 > last_result
    should_log = False
    if current_result:
        if not last_result: # 刚变绿
            should_log = True
        elif last_user_id != best_user_id: # 换人了
            should_log = True
        elif last_user_id == best_user_id and time_diff > TIME_THRESHOLD: # 超时了
            should_log = True

    if should_log:
        print(f"ACTION: 记录日志 - 用户: {best_user_id}", flush=True)
        # 写入 SQL
        log_cursor.execute(
            "INSERT INTO access_log (user_id, access_time, similarity) VALUES (?, ?, ?)",
            (best_user_id, formatted_time_log, best_similarity)
        )
        log_conn.commit()

        # 文件保存命名
        file_time_str = current_time.strftime('%Y-%m-%d_%H-%M-%S')
        image_path = os.path.join(IMG_SAVE_DIR, f"{best_user_id}_{file_time_str}.jpg")
        label_path = os.path.join(LABEL_SAVE_DIR, f"{best_user_id}_{file_time_str}.txt")
        
        # 保存图片
        cv2.imwrite(image_path, frame)

        # 保存标签
        if len(faces) > 0:
            with open(label_path, "w", encoding='utf-8') as f:
                x1, y1, x2, y2 = faces[0].bbox
                f.write(f"左上角坐标：({x1:.2f},{y1:.2f}) 右下角坐标：({x2:.2f},{y2:.2f})\n")

    last_result = current_result

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("ACTION: 退出", flush=True)
        break
    
    title = "Detect (Mock)" if config.USE_STATIC_IMAGE else "Detect (Real)"
    cv2.imshow(title, frame)

# 释放
camera.release()
cv2.destroyAllWindows()
conn.close()
log_conn.close()