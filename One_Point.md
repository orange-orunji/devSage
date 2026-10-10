**这个项目是做什么的**
```aiignore
基于langchain构建本地存储向量检索的知识库问答系统，包含多层检索
```

**项目有什么限制**
```aiignore
- 依赖外部 API（DeepSeek LLM / 智谱 Embedding），无网络不可用
- 仅支持单用户本地部署，未做多租户隔离
- 大文件（>10MB）上传性能较差
```

**RAG链路是怎么搭的**
```aiignore
1. 文档上传 → 解析（PDF/Word/Markdown/TXT）
2. 文本分割 → 向量化 → 存入 Chroma 向量库
3. 用户提问 → HyDE 假设文档生成 → 向量检索 + BM25 关键词检索
4. BGE-Reranker 重排序 → LLM 生成回答 → 流式返回前端
```

**混合检索和Rerank是怎么做的**
```aiignore
HyDE 生成假设文档后同时走向量检索和 BM25 关键词检索，合并结果后用 BGE-Reranker 重排序，取 Top-K 作为最终上下文
```

**评估数据是怎么来的**
```aiignore
项目中包含一个手工构造的模糊问题和精确问题`eval_questions.json` ，通过 `eval_retrieval.py` 自动计算 Recall@K 和 MRR
优化后  召回率Hit Rate top_1 0.53 提升到0.67
```
