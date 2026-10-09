from app.services.embedding_factory import get_embedding
from langchain_chroma import Chroma

from app.config.settings import get_settings

"""向量检索类"""
class VectorStoreService:
    def __init__(self, embedding_model=None):
        self.embedding = embedding_model
        self.s = get_settings()
        # 想用框架自带的HyDe检索,但好像换包了暂时找不到位置先遗弃此方案
        self.base_embedding = get_embedding()
        # self.hyde_retrieve = HypotheticalDocumentEmbedder.from_llm(llm=self.llm,
        #                                                       base_embeddings=self.base_embedding,
        #                                                       prompt=PromptTemplate.from_template(
        #                                                           "请根据问题写一段可能出现在相关文档中的答案。\n问题：{question}\n假设文档："
        #                                                       ))
        self.chroma = Chroma(
            embedding_function=self.base_embedding,
            persist_directory=self.s.CHROMA_DIR,
            collection_name=self.s.CHROMA_NAME
        )

    def get_vector(self, query: str, k: int = 3):
        return self.chroma.similarity_search(query, k=k)

    def get_all_documents(self) -> list:
        """
        获取chroma中全部数据
        :return:
        """
        data = self.chroma.get()

        from langchain_core.documents import Document
        return [
            Document(page_content=text, metadata=meta)
            for text,meta in zip(data['documents'],data['metadatas'])
        ]

#     创建唯一实体，防止重复创建
vector_store_service = VectorStoreService()

