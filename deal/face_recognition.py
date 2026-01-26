# deal/face_recognition.py
import cv2
import sqlite3
import sys
import config
from camera_utils import SmartCamera
from insightface.app import FaceAnalysis

# 防止乱码
sys.stdout.reconfigure(encoding='utf-8')

def init_db():
    """初始化数据库连接"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        embedding BLOB)''')
    conn.commit()
    return conn, cursor

def main():
    print("DEBUG: === 启动人脸录入程序 ===", flush=True)

    # 1. 初始化组件
    try:
        # 摄像头
        camera = SmartCamera()
        # 数据库
        conn, cursor = init_db()
        # AI 模型
        print("DEBUG: 正在加载 AI 模型...", flush=True)
        app = FaceAnalysis(name=config.MODEL_NAME)
        app.prepare(ctx_id=0, det_size=config.DET_SIZE)
        print("DEBUG: 模型加载完毕", flush=True)
    except Exception as e:
        print(f"ERROR: 初始化失败 - {e}", flush=True)
        return

    print("DEBUG: 等待用户操作...", flush=True)
    registered_embedding = None

    # 2. 主循环
    while True:
        ret, frame = camera.read()
        if not ret:
            print("WARNING: 无法读取画面", flush=True)
            break

        # AI 推理
        faces = app.get(frame)

        if len(faces) > 0:
            # 取第一张脸
            face = faces[0]
            
            # 绘制提示语
            if registered_embedding is None:
                cv2.putText(frame, "Press R to Register", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Registered Done!", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
            # 键盘监听
            key = cv2.waitKey(1) & 0xFF
            
            # 按 R 注册
            if key == ord('r') and registered_embedding is None:
                registered_embedding = face.embedding
                embedding_bytes = registered_embedding.tobytes()
                
                try:
                    cursor.execute("INSERT OR REPLACE INTO users (user_id, embedding) VALUES (?, ?)", 
                                (config.DEFAULT_REGISTER_ID, embedding_bytes))
                    conn.commit()
                    print(f"ACTION: >>> 用户 [{config.DEFAULT_REGISTER_ID}] 人脸已注册成功！", flush=True)
                except Exception as e:
                    print(f"ERROR: 数据库写入失败 - {e}", flush=True)

        # 按 Q 退出
        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            print("ACTION: 用户退出", flush=True)
            break

        title = "Register Mode (Image)" if config.USE_STATIC_IMAGE else "Register Mode (Camera)"
        cv2.imshow(title, frame)

    # 清理
    camera.release()
    cv2.destroyAllWindows()
    conn.close()

if __name__ == "__main__":
    main()