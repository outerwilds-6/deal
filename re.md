# SmartStation — 本轮改动记录 & 待测试清单

## 已修改文件 (9 个)

| 文件 | 改动内容 |
|------|----------|
| `database/schemas.py` | `FaceAuthResult` 加 `exit_expected_total` / `exit_picked_count`，action 值改为 ENTRY/EXIT |
| `database/models.py` | 新增 `ParcelRepository.get_all_parcels_by_phone` + `AccessLogRepository.get_last_action` |
| `services/pickup/core.py` | `handle_pickup()` 去掉 `user_id` 参数（人脸自推断身份）；新增 `check_exit_status()` |
| `routers/client_api.py` | `/access/entry` + `/access/exit` → `/access/auth`（统一入口，后端判断进/出）；新增 `/access/exit_confirm`；`/confirm_pickup` 去掉 `user_id` 查询参数 |
| `templates/client.html` | 删除 `#state-inside` 面板；idle 面板改为"刷脸认证"+"扫码取件"两个按钮；新增 `#auth-popup` 弹窗 |
| `templates/js/client.js` | 全量重写：`handleAuth` 统一入口 → 根据 action 渲染入口/出口弹窗；取件不传 user_id；弹窗手动关闭 + 8s 超时 |
| `templates/css/client.css` | 新增弹窗/出口统计样式；`#interact-panel` 加 `position:relative`；`#auth-popup` 改为全屏绝对定位 backdrop |
| `routers/backend_api.py` | Bug 修复：补上缺失的 `import asyncio`；`delete_user` 内调用 `remove_single_face_from_cache()` |
| `services/camera_manager/real_camera.py` | **新增**：`start()` 加重试逻辑（3次/1s间隔）+ 日志打印（分辨率/后端），便于定位 RDK 启动问题 |

## 之前修复的 Bug

| Bug | 位置 | 状态 |
|-----|------|------|
| 1: 缺 `import asyncio` | `backend_api.py:11` | ✅ |
| 2: 扫描器 demo 兜底冲突 overlap QR | `scanner/core.py` + `pickup/core.py` | ✅ |
| 3: QR 尺寸太小 (0.15 ratio) | 实测 OK，不修 | ✅ |
| 4: 删除用户后缓存未清理 | `state.py` + `backend_api.py` | ✅ |
| 5: 摄像头启动失败无重试 | `real_camera.py` → 3次重试+日志 | ✅ |

## RDK 移植备忘

- **环境**：Conda `~/SMStation/env/`，Python 3.11.15
- **摄像头**：`/dev/video0` (5843:e515 USB Web Camera)，V4L2 后端，640x480@30fps
- **人脸模型**：`buffalo_s` (轻量)，CPU provider
- **RDK 本地差异**（3 个文件，勿覆盖）：
  - `requirements.txt`: 去掉了 `onnxruntime-gpu`
  - `face_recognition/constants.py`: buffalo_l→buffalo_s, CPU provider
  - `camera_manager/constants.py`: `CAMERA_TYPE = "real"`
- **启动**：`~/SMStation/env/bin/uvicorn main:app --host 0.0.0.0 --port 8000`（不要用 `--reload`，会残留摄像头句柄）
- **首次启动耗时**：~22s（InsightFace 模型加载占 ~4s，摄像头 ~0.3s）

## 已测试路径

| # | 路径 | 结果 |
|---|------|------|
| 1 | 进门刷脸 → 入口弹窗展示包裹 + 关闭 | ✅ |
| 2 | 扫码取件（无 user_id 参数） | ✅ |
| 3 | 取件重试 + 取消按钮切换 | ✅ |
| 4 | 取件成功通知 | ✅ |
| 5 | RDK 摄像头 RealCamera 640x480 BGR 帧 | ✅ |
| 6 | RDK 启动 uvicorn + 页面 200 | ✅ |

## 未测试路径（下次 session）

| # | 路径 | 涉及代码 | 风险 |
|---|------|----------|------|
| 1 | **出门流程** | `client_auth()` EXIT 分支 → `get_last_action()` → `check_exit_status()` → 前端 `showExitPopup()` | 高 |
| 2 | **出门确认** | `client_exit_confirm()` → `add_log(OUT)` → `CABINET_LOCK` WS 广播 | 高 |
| 3 | **后端注册用户** | `backend_api.py` `register_user` → `run_in_executor` | 高 |
| 4 | **删除用户 + 缓存清理** | `delete_user` → `remove_single_face_from_cache()` | 中 |
| 5 | 出口弹窗"确认离开"按钮 | `handleExitConfirm()` → 返回 idle | 中 |
| 6 | 出口弹窗"我再看看"按钮 | `dismissPopup()` | 低 |
| 7 | 入口弹窗 8s 自动关闭 | `startPopupAutoDismiss()` | 低 |
