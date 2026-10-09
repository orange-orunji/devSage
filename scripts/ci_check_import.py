"""CI 验收脚本（full-install job）：验证 requirements.txt 覆盖应用的真实 import 面。

背景（P0-1 的教训）：smoke job 装的是 requirements-ci.txt，拦不住 requirements.txt
本身缺包——所以这个脚本在「装完完整 requirements.txt」后执行，作为缺包回归的主防线。

三步，顺序有讲究：

1. stub 掉 app.services.rerank —— 它是全应用唯一在 import 阶段加载本地模型的
   模块（rerank.py:5 `_model = CrossEncoder(_MODEL_PATH)`），而 models/ 有 3.2GB
   且被 .gitignore 忽略，CI 上不存在；路径不存在时 sentence-transformers 会把
   模型路径当 HF 仓库名去下载并失败。stub 后 hyde.py 的
   `from app.services.rerank import rerank` 拿到空实现，主链其余部分全部真实导入。
2. import main —— main.py 及其完整路由 / Agent / 服务链真实导入。这条链上有
   main.py:10 的 langgraph.checkpoint.sqlite.aio（P0-1 缺陷点）、agent.py 的
   langgraph.graph / langgraph.prebuilt、chat.py 与 status_tool.py 的
   langgraph.types——requirements.txt 少声明任何被链上模块 import 的包，
   都会在这一步就地抛 ModuleNotFoundError。
3. import torch / sentence_transformers —— 重依赖单独验证。rerank 被 stub 后
   它们的导入不再被第 2 步覆盖；requirements.txt 经由
   sentence-transformers~=5.5.1 传递引入 torch，必须确认真的装上了（不加载权重）。

注意：若未来 rerank.py 新增对外符号且被主链 import（如 _model），需同步补充
stub 属性——届时这一步会以 AttributeError 就地报错，不会静默漏检。

用法：仓库根目录下  python scripts/ci_check_import.py
退出码：0 = 全部通过；1 = 缺包 / 导入失败。
"""

import sys
import types
from pathlib import Path

# `python scripts/ci_check_import.py` 的 sys.path[0] 是 scripts/，
# 显式补上仓库根，保证无论从哪个 cwd 启动都能 import main / app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── 1. stub：绕过 import 期的本地模型加载（CI 无 models/ 目录）──
rerank_stub = types.ModuleType("app.services.rerank")
rerank_stub.rerank = lambda *args, **kwargs: []
sys.modules["app.services.rerank"] = rerank_stub

# ── 2. 真实导入应用入口（覆盖 langgraph 全家 + 全部路由/服务链）──
import main  # noqa: E402

# ── 3. 重依赖显式验证（stub 令第 2 步覆盖不到它们）──
import torch  # noqa: E402
import sentence_transformers  # noqa: E402

print("ci_check_import: OK — requirements.txt 覆盖应用 import 面（rerank 已 stub）")
