import cv2
import sqlite3
import numpy as np
from insightface.app import FaceAnalysis

# 连接到数据库（如果数据库文件不存在，会自动创建）
conn = sqlite3.connect("faces.db")
cursor = conn.cursor()

# 创建用户表
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    embedding BLOB)''')
conn.commit()

#识别特定人脸
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))
#内置摄像头
cap = cv2.VideoCapture(0)

registered_embedding = None

#开始检测

#读取画面及人脸
while True:
    ret, frame = cap.read()
    if not ret:
        break
    faces = app.get(frame)

    #如果有人脸
    if len(faces) > 0:
        face = faces[0]  # 只取第一张脸（按照人脸出现的顺序）

        # TODO: 输入框输入用户名
        user_id = "XinYi_Yu"
        embedding = face.embedding
        if registered_embedding is None:
            #记录人脸
            cv2.putText(frame, "Press R to Register", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        #神秘的人脸识别
        if registered_embedding is not None:
            similarity = np.dot(embedding, registered_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(registered_embedding)
            )
            #输出识别结果
            if similarity > 0.5:
                text = "Access Granted"
                color = (0, 255, 0)
            else:
                text = "Access Denied"
                color = (0, 0, 255)
            #把结果放在头上
            cv2.putText(frame, f"{text} ({similarity:.2f})",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    #TODO:按键注册、按键关闭
    #按下r来注册
    key = cv2.waitKey(1) & 0xFF
    if key == ord('r') and len(faces) > 0 and registered_embedding is None:
        registered_embedding = faces[0].embedding
        # 将 embedding 转换为二进制格式 转换为BLOB类型
        embedding_bytes = registered_embedding.tobytes()
        # 插入用户数据
        cursor.execute("INSERT OR REPLACE INTO users (user_id, embedding) VALUES (?, ?)", 
                    (user_id, embedding_bytes))
        conn.commit()
        print("人脸已注册")

    if key == ord('q'):
        break
    cv2.imshow("Face Recognition", frame)
cap.release()
cv2.destroyAllWindows()