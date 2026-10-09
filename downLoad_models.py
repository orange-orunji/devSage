import os
from huggingface_hub import snapshot_download

# 国内镜像站
endpoint = "https://hf-mirror.com"
# 模型名称
repo_id = "BAAI/bge-reranker-base"
# 下载到项目里的 models 文件夹
local_dir = os.path.join(os.path.dirname(__file__), "models", "bge-reranker-base")

print(f"开始下载模型到: {local_dir}")
# 下载会自动续传，无需额外参数
snapshot_download(
    repo_id=repo_id,
    local_dir=local_dir,
    endpoint=endpoint,
    max_workers=4                # 加快下载
)
print("下载完成！")