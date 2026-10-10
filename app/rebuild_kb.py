"""
知识库重向量化脚本：更换 Embedding 模型后，把现有切片用新模型重新编码

为什么不从 app/data/report 重灌：
    上次事故后语料已扩充到 38 切片，部分新文档不在 report 目录，
    从源文件重灌会丢数据。改为直接读 Chroma 现有切片+metadata，
    删旧集合（旧模型向量空间不能与新模型混用），再重新入库。

运行：python -m app.rebuild_kb
"""
import os
import sys

# 直接运行（python app/rebuild_kb.py）时 sys.path[0] 是 app/，补上仓库根，
# 与 `python -m app.rebuild_kb` 两种跑法等价
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chroma import Chroma

from app.config.settings import get_settings
from app.services.embedding_factory import get_embedding

s = get_settings()
BATCH = 16  # 回灌分批大小，保守值


def main():
    # 打开旧集合：get() 只读文本和 metadata，不涉及向量化，embedding 随便给
    old = Chroma(
        embedding_function=get_embedding(),
        persist_directory=s.CHROMA_DIR,
        collection_name=s.CHROMA_NAME,
    )
    data = old.get(include=["documents", "metadatas"])
    docs, metas = data["documents"], data["metadatas"]
    if not docs:
        print("集合为空，无需重建")
        return
    print(f"旧集合读出 {len(docs)} 个切片（模型切换前）")

    # 删除旧集合：向量是旧模型空间编码的，留着会污染新模型的检索
    old.delete_collection()

    # 同名重建并分批回灌（get_embedding() 已是新模型）
    store = Chroma(
        embedding_function=get_embedding(),
        persist_directory=s.CHROMA_DIR,
        collection_name=s.CHROMA_NAME,
    )
    for i in range(0, len(docs), BATCH):
        store.add_texts(docs[i:i + BATCH], metadatas=metas[i:i + BATCH])
        print(f"已回灌 {min(i + BATCH, len(docs))}/{len(docs)}")

    # 抽样验证：新向量空间下的检索应返回合理结果
    r = store.similarity_search("Redis 默认持久化方式", k=1)
    print(f"\n重建完成 | 总切片数={len(docs)}")
    print("抽样检索 Top-1:", r[0].page_content[:80] if r else "无结果")


if __name__ == "__main__":
    main()
