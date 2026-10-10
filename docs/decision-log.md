# 技术决策记录（Decision Log）

> 用途：记录「为什么选 A 不选 B」的重大决策，供面试讲述与后人接手。
> 每条按：背景 → 选项 → 决策与理由 → 验证 的结构书写。

## 2026-10-10 CI 接入：smoke / full-install 双 job 分工

**背景**：requirements.txt 含 torch / sentence-transformers（GB 级），CI 全量安装
不可行；但只装裁剪过的 requirements-ci.txt 会让 P0-1 类缺陷（requirements.txt
缺包，如 langgraph-checkpoint-sqlite）在 CI 上不可见——CI 验证的对象漂移成了
「CI 专用清单」而非用户真实安装。

**选项**：

- A. 单 job 只装 requirements-ci.txt 跑 5 条 P0 冒烟——快，但拦不住
  requirements.txt 本身缺包
- B. full-install 全量装 + `import main`——最真实，但 `rerank.py:5` 在 import 期
  加载 3.2GB 本地模型（models/ 被 .gitignore 忽略），CI 需下载或缓存巨量文件
- C. 双 job：smoke（ci 清单 × ubuntu/windows 跑 P0 测试）+ full-install（完整清单，
  stub 掉模型加载后 `import main` 验证 import 面）

**决策**：C。理由：

- A 的缺口恰好就是 P0-1 的原始事故（CI 全绿、用户 clone 即崩），必须由 job 2 兜底
- B 的模型障碍用「stub `app.services.rerank` + 显式 import torch /
  sentence_transformers」化解（`scripts/ci_check_import.py`）：全应用唯一的
  import 期模型加载点就是 rerank.py:5，stub 后主链（fastapi / langgraph 全家 /
  sqlalchemy / aio-pika / redis / chroma…）仍全部真实导入；覆盖强于手写包列表
  （手列表会漏——langgraph-checkpoint-sqlite 就是先例）
- windows-latest 进矩阵：P0-5（中文 Windows 的 pip 按 GBK 解码）只跑 Linux 永远
  发现不了
- Python 3.11 对齐 Dockerfile（部署面）；本地 3.13 由探针环境日常覆盖
- full-install 预装 CPU 版 torch（~200MB）规避 PyPI Linux 默认拖 ~2.5GB CUDA
  依赖（torch 不在 requirements.txt 直接声明，由 sentence-transformers 传递引入）

**验证**：

- requirements-ci.txt 在 `_ci_probe` 干净环境（Py3.13 + Windows）5/5 绿
- ci_check_import.py 正向（全量环境通过）/ 反向（卸载 langgraph-checkpoint-sqlite
  → main.py:10 抛 ModuleNotFoundError，与 P0-1 报错签名一致）
- actionlint 1.7.12 零错误；action 版本（checkout@v7 / setup-python@v7 /
  cache@v6）与输入参数逐一对照官方 tagged action.yml 核实；关键 wheel
  （torch CPU / chromadb cp39-abi3 / numpy / onnxruntime / grpcio）的 cp311
  可用性经 PyPI / 官方索引确认

**已知限制**：CPU-torch 规避 CUDA 的实际耗时需 CI 首跑确认；README 徽章在
workflow 落到 master 前显示为 unknown。

## 2026-10-10 DASHSCOPE_API_KEY 空串防护：配置显式化（CI 全红牵出）

**背景**：CI 双 job 首跑全红——smoke 的 P0-2（test_vector_store_imports_without_openai_key）
与 full-install 的 `import main` 同链失败，根因不在代码而在 workflow 的 env：
只占位了 SILICON_API_KEY / SMTP_*，漏了 DASHSCOPE_API_KEY。CI 上没有 .env，
settings 取默认值 `""`，`OpenAIEmbeddings(api_key="")`（embedding_factory.py）在
client 构造时抛 `OpenAIError: Missing credentials ... OPENAI_API_KEY`。
深层暴露面：vector_store.py 模块级实例化（P0-2 修复后的现状）使 import 即构造，
embedding 工厂被 vector_store / semantic_cache / KnowledgeBase_md5_service
三处模块级共享，一处空串全链皆崩。

**机制核查**（实测 langchain-openai 1.3.5 / openai 2.45.0，修正了最初的前提）：

- openai SDK 的 env 兜底只发生在 `api_key=None`（根本不传）时；显式空串原样
  保留，缺凭证判定是 falsy 检查 → 空串 = 构造即炸，且 OPENAI_API_KEY **不被读取**
- 因此「拿错 key 连 DashScope」在当前锁定版本上不成立；真实危害是：
  ① 失败时点晚于配置校验（uvicorn 启动崩 / Docker 容器 unless-stopped 无限重启）；
  ② 报错指向本项目不存在的配置项 OPENAI_API_KEY，且照报错 export 也修不好（空串
  短路了 env 读取），排障方向被误导；
  ③ 该行为是 SDK 实现细节而非契约——未来若 SDK 对空串也兜底，会退化成真正的错连

**选项**：

- A. workflow env 补占位——必做（CI 无 .env），但只治 CI 不治模式
- B. settings 必填（`DASHSCOPE_API_KEY: str`）——必填只拦「未配置」，拦不住
  「配置了但为空串」：.env 写 `KEY=`（占位忘填）、Docker env_file 空值、CI 键
  不带值，三条路径都产生空串，恰是 Docker 无限重启的触发路径
- B+. `Field(..., min_length=1)`——把空串这一档也盖住
- C. 工厂层守卫（get_embedding 空串时 raise 带指引的错误）
- D. 传哨兵值绕开 SDK 兜底

**决策**：A + B+，不做 C / D。理由：

- B+ 后工厂永远拿不到空串（get_settings 是 lru_cache 单例，校验先行），C 是死代码
- 失败时点最早（settings 构造即 ValidationError，字段直接点名），报错从误导性的
  "Missing credentials ... OPENAI_API_KEY" 变为 pydantic 点名 DASHSCOPE_API_KEY
- 与 SILICON_API_KEY / SMTP_* 的既有必填约定一致，是 P0-4「配置显式化」精神的延续
- D 与 SDK 实现细节搏斗，脆弱

**验证**：

- 空串注入（shell 环境变量覆盖 .env）→ ValidationError 点名 DASHSCOPE_API_KEY
  （string_too_short, min_length=1）✅
- 正常值通过；5 条 P0 冒烟测试全绿，无回归
- workflow env 补 DASHSCOPE_API_KEY 占位；requirements-ci.txt 头注释同步为
  「SILICON_API_KEY / DASHSCOPE_API_KEY 均为必填」

**边界说明**：BOCHA_API_KEY 仍默认 `""`——联网兜底是可选功能，key 缺失属功能
降级而非崩溃，不套用本决策；CI 占位值只为满足「配置面存在」，真实 key 永远
不进 workflow（冒烟与 import 面检查均不发网络请求）。
