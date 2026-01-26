# deal/use_data_to_detect.py
import cv2
import sqlite3
import numpy as np
import sys
import config
from camera_utils import SmartCamera
from insightface.app import FaceAnalysis

# 防止乱码
sys.stdout.reconfigure(encoding='utf-8')

def load_users():
    """从数据库加载所有用户特征"""
    if not os.path.exists(config.DB_PATH):
        print("ERROR: 数据库文件不存在，请先运行录入脚本！", flush=True)
        return []
    
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, embedding FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows

import os # 上面漏了 import os，补在这里

def main():
    print("DEBUG: === 启动人脸核验程序 ===", flush=True)

    # 1. 加载用户数据
    users = load_users()
    print(f"DEBUG: 已加载 {len(users)} 个用户数据", flush=True)
    if len(users) == 0:
        print("WARNING: 数据库为空，请先注册。", flush=True)

    # 2. 初始化组件
    try:
        camera = SmartCamera()
        print("DEBUG: 正在加载 AI 模型...", flush=True)
        app = FaceAnalysis(name=config.MODEL_NAME)
        app.prepare(ctx_id=0, det_size=config.DET_SIZE)
        print("DEBUG: 模型加载完毕", flush=True)
    except Exception as e:
        print(f"ERROR: 初始化失败 - {e}", flush=True)
        return

    # 3. 主循环
    while True:
        ret, frame = camera.read()
        if not ret:
            break
        
        # 每一帧重置状态
        best_user_id = "Unknown"
        best_similarity = -1.0
        
        # AI 推理
        faces = app.get(frame)

        if len(faces) > 0:
            face = faces[0]
            current_embedding = face.embedding
            
            # 遍历数据库匹配
            for user_id_db, embedding_bytes in users:
                registered_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                
                # 计算余弦相似度
                similarity = np.dot(current_embedding, registered_embedding) / (
                    np.linalg.norm(current_embedding) *
                    np.linalg.norm(registered_embedding)
                )
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_user_id = user_id_db
            
            # 显示结果
            if best_similarity > config.SIMILARITY_THRESHOLD:
                color = (0, 255, 0) # Green
                status_text = "Access Granted"
            else:
                color = (0, 0, 255) # Red
                status_text = "Access Denied"
            
            # 绘制文字
            cv2.putText(frame, f"{status_text} ({best_similarity:.2f})",
                        (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            if best_similarity > config.SIMILARITY_THRESHOLD:
                cv2.putText(frame, f"ID: {best_user_id}",
                            (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        # 退出控制
        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            print("ACTION: 退出核验", flush=True)
            break
        
        title = "Detect Mode (Image)" if config.USE_STATIC_IMAGE else "Detect Mode (Camera)"
        cv2.imshow(title, frame)

    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()