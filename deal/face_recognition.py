import cv2
import sqlite3
import numpy as np
import os
import sys
import time
from insightface.app import FaceAnalysis
from camera_utils import SmartCamera
import config

# 防止输出乱码
sys.stdout.reconfigure(encoding='utf-8')

# === 1. 接收网页传来的用户名 ===
if len(sys.argv) > 1:
    TARGET_USER_ID = sys.argv[1]
else:
    TARGET_USER_ID = "Unknown_User"

print(f"DEBUG: 启动鼠标交互注册，目标用户: {TARGET_USER_ID}", flush=True)

# === 2. 初始化环境 ===
# 确保使用绝对路径，防止 Web 调用时路径错误
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "faces.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, embedding BLOB)''')
conn.commit()

print("DEBUG: 加载 AI 模型...", flush=True)
app = FaceAnalysis(name=config.MODEL_NAME, providers=config.PROVIDERS)
# 只有在 config.py 里配置了 providers 才有 GPU，否则默认 CPU
providers = getattr(config, 'PROVIDERS', ['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=config.DET_SIZE)

try:
    camera = SmartCamera()
except Exception as e:
    print(f"ERROR: 摄像头初始化失败: {e}", flush=True)
    sys.exit(1)

# === 3. 鼠标回调与 UI 逻辑 ===
mouse_pos = (0, 0)
click_event = None
current_state = 'waiting' # waiting | registered

def on_mouse(event, x, y, flags, param):
    global mouse_pos, click_event
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_pos = (x, y)
    elif event == cv2.EVENT_LBUTTONDOWN:
        click_event = 'click'

window_name = f"Register: {TARGET_USER_ID}"
cv2.namedWindow(window_name)
cv2.setMouseCallback(window_name, on_mouse)

# 按钮布局参数
BTN_H = 50
MARGIN = 20

def draw_buttons(img):
    h, w = img.shape[:2]
    
    # 定义两个按钮的区域
    # 左边：Register (绿色)
    btn_reg_rect = (MARGIN, h - BTN_H - MARGIN, w // 2 - MARGIN - 10, h - MARGIN)
    # 右边：Exit (红色)
    btn_exit_rect = (w // 2 + 10, h - BTN_H - MARGIN, w - MARGIN, h - MARGIN)

    mx, my = mouse_pos
    
    # --- 绘制注册按钮 ---
    x1, y1, x2, y2 = btn_reg_rect
    hover_reg = (x1 <= mx <= x2 and y1 <= my <= y2)
    
    if current_state == 'registered':
        color = (100, 100, 100) # 灰色 (已完成)
        text = "Done / Updated"
    else:
        color = (0, 200, 0) if not hover_reg else (50, 255, 50) # 亮绿/暗绿
        text = "CLICK TO REGISTER"
    
    cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
    # 文字居中稍微简略点处理
    cv2.putText(img, text, (x1 + 20, y1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    # --- 绘制退出按钮 ---
    x1, y1, x2, y2 = btn_exit_rect
    hover_exit = (x1 <= mx <= x2 and y1 <= my <= y2)
    color = (0, 0, 180) if not hover_exit else (50, 50, 255) # 红
    
    cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
    cv2.putText(img, "EXIT", (x1 + 60, y1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    return hover_reg, hover_exit

# === 4. 主循环 ===
last_inference_time = 0
current_faces = []

print("DEBUG: 窗口已启动", flush=True)

while True:
    ret, frame = camera.read()
    if not ret: break

    # 统一大小，方便画按钮
    frame = cv2.resize(frame, (640, 480))

    # 抽帧检测 (防止卡顿)
    now = time.time()
    # 如果你 config.py 里没有 INFERENCE_INTERVAL，这里默认 0.1
    interval = getattr(config, 'INFERENCE_INTERVAL', 0.1) 
    
    if now - last_inference_time > interval:
        current_faces = app.get(frame)
        last_inference_time = now

    # 绘制人脸框
    for face in current_faces:
        box = face.bbox.astype(int)
        color = (0, 255, 0) if current_state == 'registered' else (0, 255, 255)
        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)

    # 绘制 UI
    hover_reg, hover_exit = draw_buttons(frame)

    # 处理点击事件
    if click_event == 'click':
        if hover_exit:
            print("ACTION: 用户点击退出", flush=True)
            break
        
        if hover_reg:
            if len(current_faces) > 0:
                # 执行录入
                face = current_faces[0]
                embedding = face.embedding.tobytes()
                cursor.execute("INSERT OR REPLACE INTO users (user_id, embedding) VALUES (?, ?)", 
                            (TARGET_USER_ID, embedding))
                conn.commit()
                current_state = 'registered'
                print(f"SUCCESS: 用户 {TARGET_USER_ID} 已录入数据库", flush=True)
            else:
                print("WARNING: 没有检测到人脸，无法录入", flush=True)
    
    click_event = None # 重置点击

    # 状态文字
    cv2.putText(frame, f"User: {TARGET_USER_ID}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow(window_name, frame)

    # 按 Q 也能退
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()
conn.close()