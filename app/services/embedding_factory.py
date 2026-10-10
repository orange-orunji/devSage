from langchain_openai import OpenAIEmbeddings

from app.config.settings import get_settings

"""
统一 Embedding 工厂

所有向量化接入点（vector_store / KnowledgeBase_md5_service / semantic_cache）
必须通过 get_embedding() 获取模型，禁止各自硬编码——
上次换 text-embedding-v4 时三处散落的初始化就是教训。

切换供应商/模型只需改 settings 的 EMBEDDING_API_KEY / EMBEDDING_BASE_URL /
EMBEDDING_MODEL 三项（OpenAI 兼容接口，当前：智谱 embedding-3），
但换供应商或换模型 = 换向量空间，必须执行 python -m app.rebuild_kb 全量重建知识库。

历史备注：曾短暂切过 tongyi-embedding-vision-plus（多模态模型，不支持
OpenAI 兼容接口，需 dashscope.MultiModalEmbedding 原生 SDK 封装），
后因 text-embedding-v4 按量付费成本极低（0.5 元/百万 Token）切回。
"""


def get_embedding() -> OpenAIEmbeddings:
    s = get_settings()
    return OpenAIEmbeddings(
        model=s.EMBEDDING_MODEL,
        base_url=s.EMBEDDING_BASE_URL,
        api_key=s.EMBEDDING_API_KEY,
        # 新版 langchain-openai 默认本地 tokenize 后传 token ID 数组，
        # OpenAI 兼容接口（智谱/百炼等）只收原始字符串，必须关掉（旧版默认就是关的）
        check_embedding_ctx_length=False,
    )
