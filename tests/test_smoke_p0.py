"""P0 冒烟测试：把已复现的部署/环境类 P0 问题固化为自动化测试。

当前预期：5 条全部 FAILED。每条测试断言的都是「修复后的正确行为」，
失败即对应一个已复现、待修复的 P0 bug；业务代码修复后对应测试应转绿。
若某条测试意外通过，先怀疑复现环境不对（见下），而不是 bug 不存在。

⚠ 运行环境（换人接手先读这段）：
    必须用项目根目录的干净解释器 _clean_venv，并显式清掉
    OPENAI_API_KEY 后运行（项目根目录、bash 下）：

        env -u OPENAI_API_KEY PYTHONIOENCODING=utf-8 \
            _clean_venv/Scripts/python.exe -m pytest -v

    （PYTHONIOENCODING=utf-8 只是让 pytest 输出在中文 Windows 控制台
      不乱码，不影响测试结果。）
    不要用 .venv——那是本机「脏」环境，会掩盖本套件要复现的问题：
      - 装了 langgraph-checkpoint-sqlite → P0-1 虚假通过
      - 可能设置了 OPENAI_API_KEY      → P0-2 复现前提被破坏
"""

import codecs
import importlib
import sys
from pathlib import Path


def test_langgraph_sqlite_checkpointer_available():
    """P0-1：干净环境缺 langgraph 的 sqlite checkpointer 依赖包。

    Bug：main.py:10 的 `from langgraph.checkpoint.sqlite.aio import
    AsyncSqliteSaver` 依赖 langgraph.checkpoint.sqlite 子模块，该子模块
    由独立包 langgraph-checkpoint-sqlite 提供；而 requirements.txt 只声明
    了 langgraph~=1.2.9，不带这个包。

    触发环境：任何按 requirements.txt 全新安装依赖的机器（_clean_venv、
    Docker 构建、新同事环境）——依赖装完后启动即抛
    ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'。
    """
    module = importlib.import_module("langgraph.checkpoint.sqlite.aio")
    assert hasattr(module, "AsyncSqliteSaver"), (
        "langgraph.checkpoint.sqlite.aio 可导入，但缺少 AsyncSqliteSaver"
    )


def test_vector_store_imports_without_openai_key(monkeypatch):
    """P0-2：vector_store 在 import 阶段创建 OpenAI 客户端，无 key 即炸。

    Bug：vector_store.py:12 在 VectorStoreService.__init__ 里创建了不传
    api_key 的 ChatOpenAI（openai SDK 此时只会去找进程环境变量
    OPENAI_API_KEY，而项目实际用的是 settings 里的 SILICON_API_KEY）；
    且模块底部 `vector_store_service = VectorStoreService()`（:48）让
    这次初始化在 import 时就执行。于是只要进程没有 OPENAI_API_KEY，
    `import app.services.vector_store` 就抛
    openai.OpenAIError: Missing credentials——「导入模块」产生了构建
    OpenAI 客户端的副作用。

    触发环境：.env 齐全但进程未导出 OPENAI_API_KEY 的任何 shell/CI
    （本项目 key 走 SILICON_API_KEY，部署机通常不会设置
    OPENAI_API_KEY；典型受害者：跑测试、打包、静态检查等
    「只是 import 一下」的场景）。
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # 强制重新执行模块顶层代码，避免命中本次会话已缓存的导入结果
    sys.modules.pop("app.services.vector_store", None)
    module = importlib.import_module("app.services.vector_store")
    assert hasattr(module, "VectorStoreService"), (
        "app.services.vector_store 应导出 VectorStoreService"
    )


def test_bm25_service_handles_empty_corpus():
    """P0-3：BM25 service 层没有空语料守卫，空知识库直接崩。

    Bug：bm25_service.py:24（build_index）和 :50（add_documents）把（可能
    为空的）分词语料直接喂给 BM25Okapi；而 rank_bm25 0.2.2 在空语料下
    构造即除零（rank_bm25.py:52：avgdl = num_doc / self.corpus_size），
    ZeroDivisionError: division by zero。

    触发环境：知识库为空（全新部署还没导入文档、或全量删除文档后）时，
    启动流程执行 BM25 全量索引重建（build_index 收到空列表）；或空批次
    文档的增量写入（add_documents 收到空列表）。空库是系统冷启动的合法
    状态，不应崩溃。

    修复位置约定：rank_bm25 是第三方库、永远不会去改它——空语料守卫
    加在我们自己的 service 层，所以本测试只针对 BM25Service 的对外
    方法，不直接断言 BM25Okapi([])。
    """
    from app.services.bm25_service import BM25Service

    # 底层库在空语料下会 ZeroDivisionError（rank_bm25.py:52），
    # 守卫在我们的 service 层——这里只测 BM25Service 的对外方法。
    service = BM25Service()
    service.build_index([])      # 冷启动：空知识库全量建索引
    service.add_documents([])    # 空批次增量写入
    assert service.search("空库下的任意查询") == []


def test_settings_have_safe_defaults():
    """P0-4：settings 把开发机内网 IP 硬编码为默认配置。

    Bug：settings.py:79 的 `RABBITMQ_HOST: str = "192.168.161.128"` 把
    某台开发机的内网 IP 写死成默认值；在任何其它机器上部署且未显式
    配置该环境变量时，Worker 会静默连向这台不存在的 RabbitMQ。

    触发环境：任何非该内网段的部署环境（未设置 RABBITMQ_HOST 时）。

    范围说明：SMTP 的文档一致性（SMTP_HOST / SMTP_USER / SMTP_PASSWORD
    要么有默认值、要么被显式标注为必填）靠人工确认——那是文档与代码
    不一致的问题，不适合写单元测试；本测试只覆盖 RABBITMQ_HOST。
    """
    from app.config.settings import settings as AppSettings

    fields = AppSettings.model_fields

    assert "RABBITMQ_HOST" in fields, "settings 未声明 RABBITMQ_HOST"
    actual = fields["RABBITMQ_HOST"].get_default()
    assert actual != "192.168.161.128", (
        f"RABBITMQ_HOST 默认值 {actual!r} 是硬编码的开发机内网 IP，"
        "其它机器部署时会静默连向不存在的 RabbitMQ"
    )


def test_requirements_files_are_portable():
    """P0-5：requirements 文件含非 ASCII 字符，中文 Windows 上 pip 直接崩。

    Bug：pip 在中文 Windows 上按本地编码（GBK）解码 requirements 文件；
    requirements.txt / requirements-dev.txt / requirements-ui.txt 三个文件
    都写了中文注释且没有 UTF-8 BOM（requirements.txt 的表格线 ═ 从偏移 2
    起即非 ASCII），pip install -r 时抛
    UnicodeDecodeError: 'gbk' codec can't decode byte ...

    触发环境：区域设置为「中文(简体, 中国)」的 Windows 上执行
    pip install -r requirements.txt（新同事装机、Windows CI runner）。

    合规标准（满足其一即可）：纯 ASCII（在任何本地编码下都安全），
    或带 UTF-8 BOM（pip 识别 BOM 后按 UTF-8 解码）。

    检查方式：先收集全部不合格文件，再一次性断言——失败信息一次列全，
    修复时不用跑两轮。
    """
    project_root = Path(__file__).resolve().parent.parent
    violations = []
    for name in ("requirements.txt", "requirements-dev.txt", "requirements-ui.txt"):
        path = project_root / name
        if not path.is_file():
            violations.append(f"{name} 不存在")
            continue
        data = path.read_bytes()
        if all(byte < 0x80 for byte in data) or data.startswith(codecs.BOM_UTF8):
            continue
        first_non_ascii = next(i for i, b in enumerate(data) if b >= 0x80)
        violations.append(
            f"{name}：含非 ASCII 字节（首个位于偏移 {first_non_ascii}）"
            "且无 UTF-8 BOM"
        )
    assert not violations, (
        "以下 requirements 文件在中文 Windows 上无法被 pip 安全解码"
        "（pip 按本地 GBK 解码，pip install -r 会抛 UnicodeDecodeError；"
        "需纯 ASCII 或带 UTF-8 BOM）：\n  - " + "\n  - ".join(violations)
    )
