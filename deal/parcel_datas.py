# -*- coding: utf-8 -*-
"""
快递信息模块
"""
import sqlite3
from datetime import datetime

PARCEL_DB_NAME = "parcel_datas.db"
#客户端姓名读取谁是存入快递的操作员
OPERTATOR = "XinYi_Yu"
#客户端姓名读取谁是取走快递的人
PICKER = "Yu_XinYi"

# =======================
# 数据库初始化
# =======================
def init_db():
    conn = sqlite3.connect(PARCEL_DB_NAME)
    cur = conn.cursor()
    #包裹信息数据库
    cur.execute("""
    CREATE TABLE IF NOT EXISTS parcel (
        parcel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_no TEXT UNIQUE NOT NULL,
        company TEXT,
        receiver_name TEXT NOT NULL,
        receiver_phone TEXT NOT NULL,
        status INTEGER NOT NULL,
        location TEXT,
        in_time TEXT,
        out_time TEXT,
        remark TEXT
    )
    """)
    #使用记录数据库
    cur.execute("""
    CREATE TABLE IF NOT EXISTS parcel_status_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        parcel_id INTEGER,
        old_status INTEGER,
        new_status INTEGER,
        change_time TEXT,
        operator TEXT
    )
    """)

    conn.commit()
    conn.close()

# =======================
# 包裹状态定义
# =======================

STATUS = {
    0: "未入库",
    1: "待取件",
    2: "已取件",
    999: "异常，需要人员处理",
}

# =======================
# 获取包裹信息：
# 使用数据（快递单号，快递公司，取件人姓名，取件人手机号）
# 使用网上数据，初步记录包裹信息
# =======================
def receive_new_parcel(tracking_no, company, receiver_name, receiver_phone):
    conn = sqlite3.connect(PARCEL_DB_NAME)
    cur = conn.cursor()
    #网上信息录入
    parcel_id = cur.lastrowid #数据库中统一id
    cur.execute("""
    INSERT INTO parcel (
        parcel_id,
        tracking_no, 
        company,
        receiver_name, 
        receiver_phone,
        status
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, (parcel_id, tracking_no, company, receiver_name, receiver_phone, 0))
    conn.commit()
    conn.close()
    print(f"[网上信息记录成功] 单号:{tracking_no} 状态:未入库")

# =======================
# 存入包裹：
# 使用数据（快递单号，快递公司，取件人姓名，取件人手机号，包裹位置）
# =======================
def add_parcel(tracking_no, company, receiver_name, receiver_phone, location):
    conn = sqlite3.connect(PARCEL_DB_NAME)
    cur = conn.cursor()
    #查询包裹信息
    cur.execute("""
    SELECT parcel_id, company, receiver_name, receiver_phone, status
    FROM parcel
    WHERE tracking_no = ?
    """, (tracking_no,))
    row = cur.fetchone()

    #是否入库判断
    if not row:
        print("[入库失败] 未找到对应快递")
        return
    parcel_id, db_company, db_name, db_phone, status = row
    # 状态校验
    if status != 0:
        print("[入库失败] 包裹状态异常，不能重复入库")
        return
    # 信息一致性校验
    if db_company != company or db_name != receiver_name or db_phone != receiver_phone:
        print("[入库失败] 入库信息与网上信息不一致")
        return

    #入库成功
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    UPDATE parcel
    SET status = 1,
        location = ?,
        in_time = ?
    WHERE parcel_id = ?
    """, (location, now, parcel_id))

    #操作记录录入
    cur.execute("""
    INSERT INTO parcel_status_log
    (parcel_id, old_status, new_status, change_time, operator)
    VALUES (?, ?, ?, ?, ?)
    """, (parcel_id, 0, 1, now, OPERTATOR))
    conn.commit()
    conn.close()
    print(f"[入库成功] 单号:{tracking_no} 状态:待取件")

# =======================
# 通过手机号查询：
# 使用数据（查询手机号）
# 为什么不使用姓名查询：考虑到重名情况
# =======================
def query_parcel_by_phone(phone):
    conn = sqlite3.connect(PARCEL_DB_NAME)
    cur = conn.cursor()
    cur.execute("""
    SELECT parcel_id, tracking_no, company, location, status
    FROM parcel
    WHERE receiver_phone = ?
    """, (phone,))
    rows = cur.fetchall()
    conn.close()
    print(f"[手机号查询] 手机号 {phone}")
    for r in rows:
        print(f"         快递单号:{r[1]} 快递公司：{r[2]} 位置:{r[3]} 状态:{STATUS[r[4]]}")
    return rows

# =======================
# 取件：
# 使用数据（统一id，取件人）
# 为什么需要输入取件人：同学代取功能
# =======================
def pickup_parcel(parcel_id, name):
    conn = sqlite3.connect(PARCEL_DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT status FROM parcel WHERE parcel_id = ?", (parcel_id,))
    row = cur.fetchone()

    #出库前判断
    if not row:
        print("[取件失败] 包裹不存在")
        return
    if row[0] != 1:
        print("[取件失败] 包裹不在库中")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #数据库更新
    cur.execute("""
    UPDATE parcel
    SET status = 2, out_time = ?
    WHERE parcel_id = ?
    """, (now, parcel_id))
    #操作记录录入
    cur.execute("""
    INSERT INTO parcel_status_log
    (parcel_id, old_status, new_status, change_time, operator)
    VALUES (?, ?, ?, ?, ?)
    """, (parcel_id, 1, 2, now, name))

    conn.commit()
    conn.close()
    print(f"[取件成功] 快递ID:{parcel_id} 已取件，取件者:{name}")


# =======================
# 测试主流程
# =======================

init_db()

receive_new_parcel(
    tracking_no="SF123456789",
    company="顺丰",
    receiver_name="虞昕毅",
    receiver_phone="13800000000",
)
add_parcel(
    tracking_no="SF123456789",
    company="顺丰",
    receiver_name="虞昕毅",
    receiver_phone="13800000000",
    location="A区-03柜"
)
parcels = query_parcel_by_phone("13800000000")
if parcels:
    pickup_parcel(parcels[0][0], PICKER)