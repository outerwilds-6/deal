import os
import subprocess
import sys
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings

# 1. 引入 csrf_exempt
from django.views.decorators.csrf import csrf_exempt

def index(request):
    """渲染前端主页"""
    return render(request, 'index.html')

# 2. 加上这个装饰器，表示该视图不需要 CSRF Token 检查
@csrf_exempt 
def run_script(request):
    """接收前端请求并运行脚本"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            script_name = data.get('script_name')

            # 安全检查
            if not script_name or '/' in script_name or '\\' in script_name:
                return JsonResponse({'status': 'error', 'message': '非法的文件名'})

            # 构建脚本绝对路径
            script_path = os.path.join(settings.BASE_DIR, 'deal', script_name)

            if not os.path.exists(script_path):
                return JsonResponse({'status': 'error', 'message': f'文件 {script_name} 不存在'})

            # 运行脚本
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                # 注意：如果涉及人脸识别窗口，不要设置太短的 timeout，或者去掉 timeout
                # 否则你在操作摄像头时，后台觉得脚本卡死会强行杀掉
                # timeout=30 
            )

            if result.returncode == 0:
                return JsonResponse({
                    'status': 'success', 
                    'output': result.stdout
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': f"脚本报错: {result.stderr}"
                })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': '仅支持POST请求'})