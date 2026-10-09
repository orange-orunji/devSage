import jieba
from rank_bm25 import BM25Okapi
"""
bm25得分处理功能
导入模型->查询全部文本->投喂给模型->对问题进行切片查找->返回指定相似的最高的几个
"""
class BM25Service:
    def __init__(self):
        self.documents = []
        self.tokenizes_content = []
        self.bm25 = None

    def build_index(self,documents):
        """
        构建文件的索引,初始化属性
        :param documents: 全部文件
        :return: 构建后的文件索引
        """
        # 获取初始定义的文件
        self.documents = documents
        # 切割文本
        self.tokenizes_content = [list(jieba.cut(doc.page_content)) for doc in documents]
        # 获取bm25模型并投喂切割后的文本内容
        # 空语料守卫：BM25Okapi 构造遇到空语料会除零（rank_bm25 不接受空库），置 None 表示空索引
        self.bm25 = BM25Okapi(self.tokenizes_content) if self.tokenizes_content else None

    def search(self,query : str,top_k:int=10):
        """

        :param query: 询问的问题
        :param top_k: 返回的最高相似度个数
        :return: 最高相似度得分的列表
        """
        if not self.bm25:
            return []
        # 获取当前问题的切片
        # 注意：必须传 list，不能传 [生成器]——get_scores 逐词查词频，
        # 生成器对象本身不是词，会导致全部文档得 0 分，排序退化为索引顺序
        query_cut_list = list(jieba.cut(query))
        # 投喂给bm25模型打分
        scores = self.bm25.get_scores(query_cut_list)
        # 按分数排序，取 top_k 的下标
        result_rank_list = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.documents[i] for i in result_rank_list]

    # 在 BM25Service 中添加方法
    def add_documents(self, new_docs: list):
        new_tokens = [list(jieba.cut(doc.page_content)) for doc in new_docs]
        self.documents.extend(new_docs)
        self.tokenizes_content.extend(new_tokens)
        # 空语料守卫同 build_index：空语料置 None，避免 BM25Okapi 除零
        self.bm25 = BM25Okapi(self.tokenizes_content) if self.tokenizes_content else None  # BM25Okapi 本身不支持增量，但数据量小时重建也很快

bm25_service = BM25Service()