import cv2
import sqlite3
import numpy as np
from insightface.app import FaceAnalysis

#识别特定人脸
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))
#内置摄像头
cap = cv2.VideoCapture(0)

#打开sql
conn = sqlite3.connect("faces.db")
cursor = conn.cursor()

#取出所有人的信息
cursor.execute("SELECT user_id, embedding FROM users")
rows = cursor.fetchall()
#记录目前最高相似的脸
best_user_id = None
best_similarity = -1
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
        current_embedding = face.embedding #目前的人脸特征向量
        for user_id, embedding_bytes in rows:
            # 1.还原数据库中的特征向量
            registered_embedding = np.frombuffer(
                embedding_bytes, dtype=np.float32
            )
            # 2. 计算余弦相似度
            similarity = np.dot(current_embedding, registered_embedding) / (
                np.linalg.norm(current_embedding) *
                np.linalg.norm(registered_embedding)
            )
            # 3. 记录最相似的人
            if similarity > best_similarity:
                best_similarity = similarity
                best_user_id = user_id
        #输出识别结果
        # TODO : 把结果放在头上
        if similarity > 0.5:
            text_1 = "Access Granted"
            text_2 = "You Are"
            text_3 = best_user_id
            color = (0, 255, 0)
            cv2.putText(frame, f"{text_1} ({similarity:.2f})",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, f"{text_2} ",
                        (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, f"{text_3} ",
                        (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        else:
            text = "Access Denied"
            color = (0, 0, 255)
            cv2.putText(frame, f"{text} ({similarity:.2f})",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    cv2.imshow("Face Recognition", frame)
cap.release()
cv2.destroyAllWindows()