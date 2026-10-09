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
