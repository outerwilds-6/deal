import os
import subprocess
import sys
import json
import sqlite3
import signal
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# 全局变量，用于存储正在运行的子进程，以便我们可以“停止”它
current_process = None

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def run_script(request):
    global current_process
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            script_name = data.get('script_name')
            # 获取前端传来的参数列表（比如用户名）
            script_args = data.get('args', []) 

            if not script_name or '/' in script_name:
                return JsonResponse({'status': 'error', 'message': '非法文件名'})

            script_path = os.path.join(settings.BASE_DIR, 'deal', script_name)
            if not os.path.exists(script_path):
                return JsonResponse({'status': 'error', 'message': '文件不存在'})

            # 如果已有进程在运行，先杀掉
            if current_process and current_process.poll() is None:
                current_process.terminate() # 尝试温和结束
                current_process = None

            # 构造命令：python script.py arg1 arg2 ...
            cmd = [sys.executable, script_path] + script_args
            
            # 使用 Popen 而不是 run，这样是非阻塞的，不会卡住网页
            # 注意：我们去掉了 capture_output，因为现在需要非阻塞运行
            current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            return JsonResponse({'status': 'success', 'message': '脚本已启动，请查看弹出窗口'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

@csrf_exempt
def stop_script(request):
    """停止当前运行的脚本（替代按 Q 退出）"""
    global current_process
    if current_process and current_process.poll() is None:
        try:
            # Windows 下通常需要更强制的 kill
            import psutil
            parent = psutil.Process(current_process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            current_process = None
            return JsonResponse({'status': 'success', 'message': '进程已强制终止'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'停止失败: {str(e)}'})
    return JsonResponse({'status': 'success', 'message': '没有正在运行的进程'})

def get_logs(request):
    """读取 access_log.db 并返回 JSON 数据"""
    db_path = os.path.join(settings.BASE_DIR, 'deal', 'access_log.db')
    if not os.path.exists(db_path):
        return JsonResponse({'status': 'empty', 'data': []})

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 倒序查询最近的 50 条记录
        cursor.execute("SELECT log_id, user_id, access_time, similarity FROM access_log ORDER BY log_id DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()

        data = []
        for row in rows:
            # 构造图片 URL: /media/images/user_time.jpg
            # 注意：这里需要根据 access_time 拼凑出当初保存的文件名
            # 数据库存的是: 2026-02-02 12:00:00
            # 文件名存的是: 2026-02-02_12-00-00
            time_str = row[2]
            file_time_str = time_str.replace(':', '-').replace(' ', '_')
            img_url = f"/media/images/{row[1]}_{file_time_str}.jpg"

            data.append({
                'id': row[0],
                'user': row[1],
                'time': row[2],
                'sim': f"{row[3]:.2f}",
                'img': img_url
            })
        
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    
@csrf_exempt
def run_script(request):
    global current_process
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            script_name = data.get('script_name')
            script_args = data.get('args', [])

            if not script_name or '/' in script_name:
                return JsonResponse({'status': 'error', 'message': '非法文件名'})

            script_path = os.path.join(settings.BASE_DIR, 'deal', script_name)
            if not os.path.exists(script_path):
                return JsonResponse({'status': 'error', 'message': '文件不存在'})

            if current_process and current_process.poll() is None:
                current_process.terminate()
                current_process = None

            cmd = [sys.executable, script_path] + script_args
            
            # ===【关键修改在这里】===
            # 打印一下我们到底执行了什么命令，方便调试
            print(f"DEBUG: 正在执行命令: {cmd}", flush=True)

            # 去掉 stdout=... 和 stderr=...
            # 让子进程的输出直接显示在 Django 的终端窗口里
            current_process = subprocess.Popen(
                cmd,
                text=True
                # 不要加 stdout=subprocess.PIPE
                # 不要加 stderr=subprocess.PIPE
            )
            # ========================

            return JsonResponse({'status': 'success', 'message': '脚本已启动...'})

        except Exception as e:
            print(f"ERROR: 启动失败: {e}") # 打印错误
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})