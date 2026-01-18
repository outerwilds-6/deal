import cv2
import json
import numpy as np
from insightface.app import FaceAnalysis

#识别特定人脸
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))
#内置摄像头
cap = cv2.VideoCapture(0)

#只检测虞昕毅
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
        user_id = "XinYi Yu"
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
    #按下r来注册
    key = cv2.waitKey(1) & 0xFF
    if key == ord('r') and len(faces) > 0 and registered_embedding is None:
        registered_embedding = faces[0].embedding
        #将特征向量转换成列表（因为 JSON 不支持直接存储 numpy 数组）
        embedding_list = registered_embedding.tolist()
        # 数据结构
        user_data = {
            "user_id": user_id,
            "embedding": embedding_list
        }
        # 将数据存储到 JSON 文件
        with open("user_data.json", "a") as f:
            json.dump(user_data, f)
            f.write("\n")  # 每个用户的数据保存为单独的 JSON 对象
        print("人脸已注册")

    if key == ord('q'):
        break
    cv2.imshow("Face Recognition", frame)
cap.release()
cv2.destroyAllWindows()