import cv2
import sqlite3
import numpy as np
from insightface.app import FaceAnalysis
from datetime import datetime
import pytz

#识别特定人脸
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))
#内置摄像头
cap = cv2.VideoCapture(0)

#打开sql
conn = sqlite3.connect("faces.db")
cursor = conn.cursor()

#创建访问日志表（如果不存在）
log_conn = sqlite3.connect("access_log.db")
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
#变量用于通行许可变化时记录日志 True为通行 False为禁止通行
last_result = False
current_result = False
#设置时间阈值（30秒），即同一个人在多少时间内多次识别到进入只写入一次日志
TIME_THRESHOLD = 30    #单位为秒

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
            text_2 = "You Are";  text_3 = best_user_id
            color = (0, 255, 0)
            cv2.putText(frame, f"{text_1} ({similarity:.2f})",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, f"{text_2} ",
                        (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, f"{text_3} ",
                        (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            current_result = True
            #查询数据库中最后一条记录，检查是否已经记录过该结果
            log_cursor.execute("SELECT user_id, access_time FROM access_log ORDER BY log_id DESC LIMIT 1")
            last_log = log_cursor.fetchone()
            #获取当前时间
            current_time = datetime.now(pytz.timezone("Asia/Shanghai"))
            formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
            if last_log is None:
                # 数据库里还没有任何访问记录
                last_user_id = None
                time_diff = 100000 #比门槛时间大就行 按道理来说应该不用设置
            else:
                last_user_id, last_access_time_str = last_log # 获取数据库中的最后一条记录
                #比较这次与上次进入的时间，以便判断是否需要记录日志
                last_access_time_naive = datetime.strptime(last_access_time_str, "%Y-%m-%d %H:%M:%S")
                # 将无时区时间转换为带时区的时间
                last_access_time = pytz.timezone("Asia/Shanghai").localize(last_access_time_naive)
                time_diff = (current_time - last_access_time).total_seconds()
        else:
            text = "Access Denied"
            color = (0, 0, 255)
            cv2.putText(frame, f"{text} ({similarity:.2f})",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            current_result = False
        # 提交到数据库
        conn.commit()
    else:
        current_result = False
    #判断是否需要写入日志
    if current_result > last_result and ( last_user_id != best_user_id or
                                          (last_user_id == best_user_id and time_diff > TIME_THRESHOLD)):
        log_cursor.execute(
            "INSERT INTO access_log (user_id, access_time, similarity) VALUES (?, ?, ?)",
            (best_user_id,formatted_time,best_similarity)
        )
        log_conn.commit()
    last_result = current_result

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    cv2.imshow("Face Recognition", frame)
#释放
cap.release()
cv2.destroyAllWindows()