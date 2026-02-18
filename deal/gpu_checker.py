import onnxruntime as ort

print("当前安装的 ONNX Runtime 版本:", ort.__version__)
print("可用的设备提供者 (Providers):", ort.get_available_providers())

if 'CUDAExecutionProvider' in ort.get_available_providers():
    print("✅ 恭喜！检测到 NVIDIA GPU，可以使用加速！")
else:
    print("❌ 未检测到 CUDA！将使用 CPU 跑死你。")
    print("可能原因：")
    print("1. 没装 onnxruntime-gpu")
    print("2. CUDA/cuDNN 版本不匹配 (最常见)")
    print("3. 缺少 zlibwapi.dll (Windows常见)")