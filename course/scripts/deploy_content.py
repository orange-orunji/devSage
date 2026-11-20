# -*- coding: utf-8 -*-
"""正文内容：系统部署说明书（被 build_deploy.py 拼接使用）。"""

h(1, "1  概述")
h(2, "1.1  目的")
p("本文档说明智维台（OpsDesk，代码仓库 devSage）的部署方式，覆盖环境准备、配置、启动、初始化、验证与常见故障处置，使部署人员在不了解代码细节的前提下，按本文档可在 30 分钟内完成一次可用的部署。")
h(2, "1.2  适用范围")
p("适用于一期版本（master 分支，提交 36d1d48 及以后）的两类部署形态：一是基于 Docker Compose 的一键部署，用于验收演示与内网试用；二是本地开发部署，用于开发调试与测试。二期工单域不涉及额外组件，届时只需新增数据表。")
h(2, "1.3  术语")
table("术语说明", ["术语", "说明"],
      [["Compose", "Docker Compose，用一份 YAML 定义多容器编排"],
       ["数据卷", "容器外的持久化目录，重建容器不丢数据"],
       ["冒烟检查", "部署后按最小路径验证系统可用的检查"],
       ["向量库", "Chroma 本地持久化库，存放文档切片向量"],
       ["检查点库", "SQLite 文件，存放会话记忆与审批中断状态"]],
      [3.4, 11.0], center=(0,), first_bold=True)

h(1, "2  部署架构")
p("系统采用单机四容器部署：api 容器对外提供 HTTP/SSE 服务并托管前端静态资源；worker 容器消费队列执行文档解析；redis 提供缓存与上传临时文件；rabbitmq 提供异步任务队列。业务数据通过目录挂载持久化到宿主机，重建容器不影响知识库与会话，部署视图如图 1 所示。")
figure(os.path.join(IMG, "deploy.png"), "部署与网络视图", 14.6)
table("容器与端口映射", ["服务", "镜像/构建", "容器内端口", "宿主机端口", "作用"],
      [["api", "本仓库 Dockerfile", "8000", "8001", "对外服务，含前端静态资源"],
       ["worker", "本仓库 Dockerfile", "—", "—", "消费文档解析任务"],
       ["redis", "redis:7-alpine", "6379", "6380", "缓存与上传临时文件"],
       ["rabbitmq", "rabbitmq:3-management-alpine", "5672 / 15672", "5673 / 15673", "任务队列与管理台"]],
      [2.2, 5.0, 3.4, 2.6, 4.0], center=(0, 2, 3), first_bold=True)
p("说明：Compose 中 api 映射到宿主机 8001，与本地开发常用的 9000 区分开，避免同时运行冲突；文档中的访问地址以实际映射端口为准。")

h(1, "3  环境要求")
table("软硬件要求", ["项目", "最低配置", "推荐配置", "说明"],
      [["CPU / 内存", "4 核 8 GB", "8 核 16 GB", "向量召回与重排较吃内存"],
       ["磁盘", "50 GB 可用", "100 GB SSD", "镜像约 2 GB，模型与知识库另计"],
       ["操作系统", "Ubuntu 20.04 / CentOS 7", "Ubuntu 22.04 LTS", "Windows 亦可，建议 WSL2"],
       ["Docker", "20.10 及以上", "24.x + Compose v2", "需支持 buildx"],
       ["网络", "可访问模型 API", "内网 + 出口代理", "无出口需改本地模型"]],
      [3.0, 4.4, 4.4, 4.2], center=(0,), first_bold=True)
p("客户端要求：Chrome 100 或 Edge 100 以上（需支持 EventSource 以接收流式响应）；分辨率建议 1440×900 以上。")

h(1, "4  部署前准备")
h(2, "4.1  获取源码")
p("从仓库拉取代码，并确认当前提交：")
code("git clone https://github.com/orange-orunji/devSage.git\ngit log --oneline -1      # 期望为 36d1d48 或更新")
h(2, "4.2  配置环境变量")
p("复制示例配置并按实际填写。四类密钥中，模型与向量化两项为必填，SMTP 仅在需要发送邮件时必填。")
code("cp .env.example .env\n# Windows: copy .env.example .env")
table("环境变量清单", ["变量", "必填", "示例值", "说明"],
      [["SILICON_API_KEY", "是", "sk-****", "大模型接口密钥"],
       ["SILICON_BASE_URL", "是", "https://api.deepseek.com", "兼容 OpenAI 协议的地址"],
       ["SILICON_MODEL", "是", "deepseek-chat", "对话模型名"],
       ["EMBEDDING_API_KEY", "是", "****", "向量化接口密钥"],
       ["EMBEDDING_BASE_URL", "是", "https://open.bigmodel.cn/api/paas/v4", "向量化接口地址"],
       ["EMBEDDING_MODEL", "是", "embedding-3", "换模型须全量重建知识库"],
       ["SMTP_HOST / PORT", "否", "smtp.qq.com / 587", "邮件发送"],
       ["SMTP_USER / PASSWORD", "否", "xxx@qq.com / 授权码", "注意是授权码不是登录密码"],
       ["JWT_SECRET", "否", "随机长字符串", "未配置时使用默认演示密钥"],
       ["REDIS_PASSWORD", "否", "rag123456", "与 compose 中保持一致"]],
      [3.8, 1.4, 5.8, 4.5], center=(1,), first_bold=True, mono_col=0)
h(2, "4.3  外部服务准备")
p("模型与向量化接口需提前开通并确认额度；SMTP 需在邮箱后台开启服务并获取授权码；若使用联网搜索兜底，还需配置搜索服务的密钥。以上服务均通过 HTTPS 访问，若部署在内网，需在防火墙上放通出口。")
h(2, "4.4  端口与目录检查")
p("部署前确认 8001、6380、5673、15673 四个端口未被占用（Windows 可用 netstat -ano | findstr :8001 检查）；并确认 app/data 目录存在且当前用户有写权限。")

h(1, "5  Docker 一键部署")
h(2, "5.1  构建镜像")
p("Dockerfile 采用三阶段构建：node:22-alpine 编译前端得到 dist，python:3.11-slim 安装依赖，最终运行镜像只保留运行时所需文件。首次构建约 5—10 分钟，依赖层有缓存，后续修改业务代码重建通常 1 分钟内。")
code("docker compose build\ndocker compose up -d      # 后台启动四个容器\ndocker compose ps         # 查看状态，期望均为 Up")
h(2, "5.2  启动顺序与依赖")
p("Compose 通过 depends_on 保证启动顺序：redis、rabbitmq 先起，worker 依赖两者，api 依赖前三者。若某个容器反复重启，用 docker compose logs <服务名> 查看原因。")
code("docker compose logs -f api        # 查看 API 日志\ndocker compose logs -f worker     # 查看解析任务日志")
h(2, "5.3  首次启动校验")
p("服务启动后在浏览器访问 http://<服务器IP>:8001，出现登录页即表示前端与接口均正常；访问 /health 返回 {\"status\":\"ok\"} 表示后端就绪。首次启动会自动创建 users 表与检查点库，无需手工建库。")

h(1, "6  本地开发部署")
h(2, "6.1  Python 环境")
p("使用 Python 3.11 创建虚拟环境并安装依赖；依赖中包含 BM25、jieba 与向量库客户端，安装体积较大，建议预留 3 GB 空间。")
code("python -m venv .venv\n.venv\\Scripts\\activate        # Windows\nsource .venv/bin/activate     # macOS / Linux\npip install -r requirements.txt")
h(2, "6.2  前端构建")
p("后端会托管 frontend/dist 下的构建产物；若未构建，则自动回退到旧版静态页面。修改前端代码后需重新构建：")
code("cd frontend\nnpm install\nnpm run build")
h(2, "6.3  启动服务")
p("开发调试建议用 9000 端口启动，与 Compose 的 8001 区分：")
code("uvicorn main:app --host 127.0.0.1 --port 9000\n# 或直接 python main.py（默认 8000 端口，开启热重载）")
p("若需要完整的缓存与异步能力，本地另起 Redis 与 RabbitMQ：docker run -d -p 6379:6379 redis；RabbitMQ 未启动时，文档上传会降级为同步处理，功能不中断但接口不再立即返回。")

h(1, "7  数据初始化")
h(2, "7.1  数据库与检查点")
p("首次启动时由 SQLAlchemy 自动创建 users 表（含 username 唯一索引），并在 app/data 下生成 checkpoints.db（会话记忆与审批状态）。两者均无需手工执行脚本。")
h(2, "7.2  知识库导入")
p("系统支持 PDF、DOCX、Markdown、TXT 四种格式。入库有两条路径：一是界面右下角上传入口，二是命令行批量导入后重建索引。切片向量写入 Chroma 的 enterprise_knowledge 集合，原文保存在 app/data/uploads。")
code("python -m app.rebuild_kb     # 全量重建 BM25 与向量索引\npython -m app.worker         # 单独启动队列消费者（本地调试用）")
p("注意：更换 Embedding 模型等同于更换向量空间，必须全量重建，否则召回结果不可用。")
h(2, "7.3  初始账号")
p("系统没有内置管理员账号，首次使用在登录页点击“注册”创建账号即可；如需多人使用，各自注册，数据按用户隔离。")

h(1, "8  部署后验证")
p("按下表逐项验证，全部通过即视为部署成功。表中命令以 Linux 为例，Windows 用 curl.exe 替代。")
table("冒烟验证清单", ["序号", "检查项", "操作/命令", "期望结果"],
      [["1", "服务健康", "curl http://127.0.0.1:8001/health", "返回 {\"status\":\"ok\"}"],
       ["2", "首页可访问", "浏览器打开 http://<IP>:8001", "显示登录页"],
       ["3", "注册登录", "注册新账号并登录", "进入工作台，显示知识库统计"],
       ["4", "文档入库", "上传一个 txt 文件", "统计数字增加，状态变为完成"],
       ["5", "问答链路", "提问知识库内的问题", "逐字输出，句末有引用来源"],
       ["6", "工具调用", "提问“生成本周报告”", "返回报告并出现下载按钮"],
       ["7", "审批中断", "触发“发送邮件”", "弹出审批卡片，未确认不发送"],
       ["8", "会话持久", "刷新页面后继续对话", "历史仍在，上下文连贯"]],
      [1.2, 3.0, 6.4, 4.8], center=(0,), first_bold=True)

h(1, "9  常见问题处置")
table("常见故障与处置", ["现象", "可能原因", "处置方法"],
      [["启动日志提示 Redis 未连接", "未启动 Redis 或密码不一致", "启动 Redis 并核对 REDIS_PASSWORD；功能会降级但不阻断"],
       ["上传文档提示排队中不结束", "RabbitMQ 未启动或 vhost 不对", "启动 RabbitMQ，确认 vhost 为 /rag，检查 worker 日志"],
       ["问答返回 401", "模型密钥无效或额度耗尽", "核对 SILICON_API_KEY 与余额，重启 api 容器"],
       ["端口被占用", "8001/6380 已有服务", "修改 compose 中的端口映射后重启"],
       ["页面空白或样式错乱", "frontend/dist 未构建", "执行 npm run build，或使用 Docker 镜像内置产物"],
       ["Windows 控制台中文乱码", "编码非 UTF-8", "执行 chcp 65001，或在 PowerShell 设置输出编码"],
       ["向量召回结果为空", "嵌入模型更换但未重建", "执行 python -m app.rebuild_kb"]],
      [4.6, 4.4, 6.4], first_bold=True)

h(1, "10  运维与回滚")
p("备份：需要备份的是 app/data 目录与 app/app.db（含 users 表），建议每日打包一次；Redis 与 RabbitMQ 的数据卷可用 docker volume 备份，丢失后可重建。")
p("升级：拉取新代码后执行 docker compose build && docker compose up -d，镜像重建但数据卷保留；升级前建议先停 worker，避免解析任务中断。")
p("回滚：镜像层用 git checkout <旧提交> 重新构建即可；数据层若结构未变则无需回滚，结构有变时用备份的 app/data 覆盖。")
p("日志：api 与 worker 的日志用 docker compose logs 查看，应用自身日志写入 app/data/logs；慢请求与错误可在日志中按 request_id 检索。")

h(1, "11  附录")
p("目录结构（部署后关键路径）：")
code("""RAG_Personal/
├── app/
│   ├── data/
│   │   ├── uploads/          上传的原始文档
│   │   ├── storage/chroma_db 向量库（enterprise_knowledge 集合）
│   │   ├── chat_history/     会话历史（按用户分文件）
│   │   ├── report/           生成的报告
│   │   ├── avatars/          头像
│   │   └── logs/             应用日志
│   ├── app.db                SQLite（users 表）
│   └── checkpoints.db        智能体检查点
├── frontend/dist             前端构建产物（由 api 托管）
├── docker-compose.yml        四容器编排
├── Dockerfile                三阶段构建
└── .env                      环境变量（不入库）""")
p("端口一览：8001 对外服务、6380 Redis、5673 RabbitMQ、15673 RabbitMQ 管理台；容器内固定为 8000 / 6379 / 5672 / 15672。")
p("以上命令与配置均取自仓库当前版本（Dockerfile、docker-compose.yml、.env.example），如后续版本调整，以仓库文件为准。")
