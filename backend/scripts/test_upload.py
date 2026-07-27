"""测试上传和执行流程"""
import requests

BASE = "http://localhost:8000/api/v1"

# 1. 上传预览
print("1. 上传预览...")
with open("/root/uploads/1784700596552380579-T1deDC3KEv1RCvBVdK.xlsx", "rb") as f:
    r = requests.post(f"{BASE}/tasks/upload", files={"file": f})
    preview = r.json()
    print(f"   文件: {preview['filename']}")
    print(f"   行数: {preview['total_rows']}, 列数: {preview['total_columns']}")
    print(f"   列名: {preview['columns']}")
    print(f"   空值率: {dict(preview['null_stats'])}")

# 2. 上传执行
print("\n2. 上传执行...")
with open("/root/uploads/1784700596552380579-T1deDC3KEv1RCvBVdK.xlsx", "rb") as f:
    r = requests.post(f"{BASE}/tasks/upload/execute", files={"file": f})
    result = r.json()
    print(f"   任务ID: {result['task_id']}")
    print(f"   状态: {result['status']}")
    print(f"   输入: {result['input_rows']}行, 输出: {result['output_rows']}行")
    print(f"   耗时: {result['duration_ms']}ms")
    print(f"   输出列: {result['columns']}")
    if result['stats']:
        print(f"   字段统计: {result['stats']}")

# 3. 预览结果
print("\n3. 结果预览 (前5行):")
for i, row in enumerate(result['preview_rows'][:5]):
    print(f"   Row {i+1}: {row}")
