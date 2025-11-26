# 文档导航

Sport Agent MVP 的完整文档指南

---

## 📖 核心文档（按阅读顺序）

### 1. 新手入门（5分钟）

| 文档 | 用途 | 何时阅读 |
|------|------|---------|
| [README.md](README.md) | 项目概览、快速开始 | 第一次了解项目 ⭐ |
| [START_HERE.md](START_HERE.md) | 3步上手指南 | 准备开始使用 ⭐ |

### 2. 了解现状（10分钟）

| 文档 | 用途 | 何时阅读 |
|------|------|---------|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | 当前进展、系统指标、近期工作 | 了解项目状态 ⭐ |

### 3. 技术深入（30-60分钟）

| 文档 | 用途 | 何时阅读 |
|------|------|---------|
| [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) | Agent 架构设计 | 理解 Agent 工作原理 |
| [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md) | 数据摄取常见问题 | 遇到数据问题时 ⭐ |
| [docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md) | 数据库查询指南 | 需要直接查询数据时 |
| [docs/LOCAL_LLM_INTEGRATION.md](docs/LOCAL_LLM_INTEGRATION.md) | 本地 LLM 集成 | 配置 Ollama 时 |
| [docs/ZERO_HARDCODE_IMPLEMENTATION.md](docs/ZERO_HARDCODE_IMPLEMENTATION.md) | 零硬编码实现 | 理解架构设计理念 |

### 4. 问题解决

| 文档 | 用途 | 何时阅读 |
|------|------|---------|
| [docs/TEAM_ALIAS_FIX_GUIDE.md](docs/TEAM_ALIAS_FIX_GUIDE.md) | 球队别名修复 | 遇到"无法解析"警告 ⭐ |
| [docs/DATA_INTENT_GUIDE.md](docs/DATA_INTENT_GUIDE.md) | 数据意图体系 | 理解意图识别逻辑 |

---

## 🎯 按使用场景查找

### 我想快速开始使用
1. [README.md](README.md) - 项目概览
2. [START_HERE.md](START_HERE.md) - 3步上手

### 我遇到了数据摄取问题
1. [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md) - 常见问题解答 ⭐
2. [docs/TEAM_ALIAS_FIX_GUIDE.md](docs/TEAM_ALIAS_FIX_GUIDE.md) - 球队别名修复

### 我想了解项目架构
1. [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) - Agent 架构
2. [docs/ZERO_HARDCODE_IMPLEMENTATION.md](docs/ZERO_HARDCODE_IMPLEMENTATION.md) - 设计理念

### 我想查询数据库
1. [docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md) - SQL 查询示例

### 我想配置 LLM
1. [docs/LOCAL_LLM_INTEGRATION.md](docs/LOCAL_LLM_INTEGRATION.md) - Ollama 配置
2. [README.md](README.md#配置说明) - 切换 LLM 模型

### 我想了解项目进展
1. [PROJECT_STATUS.md](PROJECT_STATUS.md) - 当前状态 ⭐

---

## 📁 文档分类

### 根目录文档
- **README.md** - 项目入口（概览、快速开始、技术栈）⭐
- **START_HERE.md** - 快速开始（3步上手）⭐
- **PROJECT_STATUS.md** - 项目状态（进展、指标、近期工作）⭐
- **DOCS.md** - 本文档（文档导航）

### docs/ 技术文档
- **AGENT_ARCHITECTURE.md** - Agent 架构设计
- **DATA_INGESTION_FAQ.md** - 数据摄取FAQ（重复运行、无法解析）⭐
- **TEAM_ALIAS_FIX_GUIDE.md** - 球队别名修复指南 ⭐
- **DATABASE_QUERY_GUIDE.md** - 数据库查询指南
- **DATA_INTENT_GUIDE.md** - 数据意图体系
- **LOCAL_LLM_INTEGRATION.md** - 本地LLM集成
- **ZERO_HARDCODE_IMPLEMENTATION.md** - 零硬编码实现

---

## 🔍 常见问题快速索引

| 问题 | 文档位置 |
|------|----------|
| 如何快速开始？ | [START_HERE.md](START_HERE.md) |
| 多次运行数据摄取会重复吗？ | [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md#q1) |
| "无法解析球队名称"怎么办？ | [docs/TEAM_ALIAS_FIX_GUIDE.md](docs/TEAM_ALIAS_FIX_GUIDE.md) |
| 如何切换 LLM 模型？ | [README.md](README.md#配置说明) |
| 如何配置 Ollama？ | [docs/LOCAL_LLM_INTEGRATION.md](docs/LOCAL_LLM_INTEGRATION.md) |
| Agent 如何工作？ | [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) |
| 如何查询数据库？ | [docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md) |
| 项目当前状态？ | [PROJECT_STATUS.md](PROJECT_STATUS.md) |
| 零硬编码是什么？ | [docs/ZERO_HARDCODE_IMPLEMENTATION.md](docs/ZERO_HARDCODE_IMPLEMENTATION.md) |
| 意图识别怎么做？ | [docs/DATA_INTENT_GUIDE.md](docs/DATA_INTENT_GUIDE.md) |

---

## 📊 文档统计

- **根目录文档**: 4 个（核心）
- **技术文档**: 7 个（详细）
- **总计**: 11 个文档
- **推荐阅读时间**: 15-60 分钟（根据需求）

---

## 🎓 推荐阅读路径

### 路径 1: 快速上手（5分钟）
1. [README.md](README.md) - 了解项目
2. [START_HERE.md](START_HERE.md) - 开始使用

### 路径 2: 深入了解（30分钟）
1. [README.md](README.md) - 了解项目
2. [PROJECT_STATUS.md](PROJECT_STATUS.md) - 了解现状
3. [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) - 理解架构
4. [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md) - 了解数据层

### 路径 3: 完整学习（60分钟）
1. [README.md](README.md)
2. [START_HERE.md](START_HERE.md)
3. [PROJECT_STATUS.md](PROJECT_STATUS.md)
4. [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md)
5. [docs/ZERO_HARDCODE_IMPLEMENTATION.md](docs/ZERO_HARDCODE_IMPLEMENTATION.md)
6. [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md)
7. [docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md)

---

## 📝 文档维护说明

### 文档原则
1. **精简为主** - 避免冗余，保持精炼
2. **结构清晰** - 统一格式，易于导航
3. **实用导向** - 解决实际问题
4. **及时更新** - 代码变化时同步更新

### 最近更新
- **2025-11-26**: 文档大整理
  - ✅ 删除 7 个临时文档
  - ✅ 创建 PROJECT_STATUS.md（项目状态）
  - ✅ 创建 DOCS.md（本文档）
  - ✅ 优化 README.md（主入口）
  - ✅ 创建 DATA_INGESTION_FAQ.md（数据摄取FAQ）
  - ✅ 创建 TEAM_ALIAS_FIX_GUIDE.md（球队别名修复）

---

**建议**: 从 [README.md](README.md) 开始，然后根据需要阅读其他文档 🚀

