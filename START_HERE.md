# 从这里开始

欢迎使用Sport Agent MVP！这是一个AI足球分析助手。

---

## 快速开始（3步）

### 1. 启动服务

```bash
# 激活环境
source .venv/bin/activate

# 启动数据库
docker-compose up -d postgres redis

# 启动Ollama（本地AI模型）
brew services start ollama
```

### 2. 开始对话

```bash
# 简洁模式（推荐）
python scripts/chat_simple.py

# 完整模式
python scripts/chat_with_agent.py
```

### 3. 试试这些问题

```
曼联最近5场比赛战绩如何？
利物浦在英超排名第几？
预测曼联对利物浦谁会赢？
对比一下曼联和利物浦
```

---

## 文档导航

### 新手必读
1. [README.md](README.md) - 项目介绍
2. [START_HERE.md](START_HERE.md) - 本文档

### 深入了解
1. [FINAL_SUMMARY.md](FINAL_SUMMARY.md) - 完整项目总结
2. [PROJECT_COMPREHENSIVE_GUIDE.md](PROJECT_COMPREHENSIVE_GUIDE.md) - 全面技术指南
3. [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) - Agent架构设计

### 查找文档
[INDEX.md](INDEX.md) - 完整文档索引

---

## 目录结构

```
sport-agent-mvp/
├── README.md                   # 项目首页
├── START_HERE.md               # 本文档
├── FINAL_SUMMARY.md            # 完整总结
├── PROJECT_COMPREHENSIVE_GUIDE.md  # 全面指南
├── INDEX.md                    # 文档索引
│
├── config/                     # 配置文件
│   └── service.yaml            # 核心配置（已配置qwen2.5:3b）
│
├── docs/                       # 详细文档
│   ├── AGENT_ARCHITECTURE.md           # Agent架构
│   ├── DATABASE_QUERY_GUIDE.md         # 数据库查询
│   ├── LOCAL_LLM_INTEGRATION.md        # 本地LLM集成
│   ├── QUICK_START_GUIDE.md            # 快速开始
│   └── ZERO_HARDCODE_IMPLEMENTATION.md # 零硬编码实现
│
├── scripts/                    # 实用脚本
│   ├── chat_simple.py                  # 简洁聊天
│   ├── chat_with_agent.py              # 完整聊天
│   ├── chat_debug.py                   # 调试模式
│   ├── check_database_status.py        # 数据库检查
│   ├── manage_team_aliases.py          # 管理球队别名
│   └── quick_verify_data.py            # 数据验证
│
└── src/                        # 源代码
    ├── agent/                  # Agent核心
    ├── data_pipeline/          # 数据管道
    ├── ml/                     # 机器学习
    ├── services/api/           # FastAPI服务
    └── shared/                 # 共享模块
```

---

## 核心功能

### 1. 智能对话
- 理解中英文问题
- 自动识别意图
- 智能澄清

### 2. 数据查询
- 比赛战绩
- 积分榜排名
- 历史交锋

### 3. 比赛预测
- XGBoost模型
- 概率输出
- 关键因素分析

### 4. 深度对比
- 两队对比
- 历史交锋统计
- 实力分析

---

## 技术特点

1. **零硬编码** - 302+球队别名动态加载
2. **本地AI** - qwen2.5:3b（完全免费）
3. **中英文支持** - 智能翻译
4. **模块化架构** - 易扩展
5. **异步优先** - 高性能

---

## 常见问题

### Q: 如何配置本地AI模型？
A: 已配置好qwen2.5:3b，查看 [PROJECT_COMPREHENSIVE_GUIDE.md](PROJECT_COMPREHENSIVE_GUIDE.md)

### Q: 如何添加中文球队名？
A: 运行 `python scripts/manage_team_aliases.py`

### Q: 如何查看数据库？
A: 运行 `python scripts/check_database_status.py`

### Q: 每个文件是做什么的？
A: 查看 [FINAL_SUMMARY.md](FINAL_SUMMARY.md#目录文件详细说明)

### Q: 未来技术规划是什么？
A: 查看 [PROJECT_COMPREHENSIVE_GUIDE.md](PROJECT_COMPREHENSIVE_GUIDE.md#后续进展计划)

---

## 当前状态

- 功能完成度：87%
- 本地模型：qwen2.5:3b（已配置）
- 核心功能：可用
- 文档：完整

---

## 下一步

1. 查看完整总结：`cat FINAL_SUMMARY.md`
2. 启动对话：`python scripts/chat_simple.py`
3. 检查数据：`python scripts/check_database_status.py`

---

有问题？查看 [INDEX.md](INDEX.md) 找到对应文档。

