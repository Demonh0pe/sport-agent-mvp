# ⚽ Sport Agent MVP - AI足球分析师

**一句话说明**: 帮助足球彩票玩家做出更好的预测决策

---

## 🎯 这个项目是什么？

一个AI驱动的足球分析助手，可以：

1. **智能预测**: 告诉你哪队会赢，给出概率和理由
2. **深度分析**: 分析球队状态、历史交锋、战术克制
3. **数据查询**: 查询比赛数据、球队统计、排名信息

### 示例对话

```
你: 曼联对利物浦，谁会赢？

AI: 🔮 预测结果: 利物浦客场获胜 (86.9%)

📊 数据支撑:
1. 近期状态: 利物浦近5场3胜，曼联近5场1胜
2. 排名差距: 利物浦第1，曼联第15
3. 历史交锋: 最近一次曼联2-1获胜

⚠️ 关键因素:
- 曼联有主场优势
- 但整体实力差距明显
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动数据库

```bash
docker-compose up -d postgres redis
```

### 3. 开始对话

```bash
# 简洁模式（推荐）
python scripts/chat_simple.py

# 标准模式（显示详情）
python scripts/chat_with_agent.py
```

---

## 📁 项目结构

```
sport-agent-mvp/
├── src/
│   ├── agent/              # Agent核心逻辑
│   │   ├── core/          # 规划、执行
│   │   └── tools/         # 工具集（预测、数据查询）
│   ├── ml/                # 预测模型
│   │   ├── models/        # XGBoost模型
│   │   └── features/      # 特征工程
│   ├── data_pipeline/     # 数据管道
│   └── services/api/      # FastAPI服务
│
├── scripts/
│   ├── chat_simple.py           # 简洁聊天界面
│   ├── chat_with_agent.py       # 完整聊天界面
│   └── quick_verify_data.py     # 数据验证
│
├── models/
│   └── match_predictor_baseline.pkl  # 预测模型
│
└── docs/                  # 文档
    ├── TESTING_GUIDE.md           # 测试指南
    └── 数据真实性修复报告.md      # 数据质量报告
```

---

## 🔧 核心技术

- **Backend**: FastAPI + Python 3.10+
- **Database**: PostgreSQL + Redis
- **ML**: XGBoost + Scikit-learn
- **LLM**: DeepSeek (通过API)
- **Architecture**: DDD分层 + Agent模式

---

## 🎯 当前能力

### ✅ 已实现

- [x] 真实比赛数据（来自football-data.org API）
- [x] 预测模型（XGBoost，基于历史数据训练）
- [x] 对话Agent（理解自然语言问题）
- [x] 聊天界面（3种模式）

### 🚧 正在优化

- [ ] 预测准确率提升（当前基线）
- [ ] 更丰富的分析维度
- [ ] Web界面
- [ ] 用户系统

---

## 💬 如何使用

### 问题示例

**预测类**:
- 曼联对利物浦，谁会赢？
- 预测一下曼城和阿森纳的比赛

**数据查询**:
- 曼联最近5场比赛的战绩如何
- 利物浦在英超中处于什么地位

**分析类**:
- 分析一下曼联最近的问题
- 为什么利物浦排名第一

---

## 🧪 测试

```bash
# 验证数据质量
python scripts/quick_verify_data.py

# 运行单元测试
pytest tests/

# 性能测试
pytest tests/ -v --durations=10
```

---

## 📊 数据来源

- **比赛数据**: football-data.org API
- **覆盖联赛**: 英超、西甲、意甲、德甲、法甲
- **数据量**: 800+ 场比赛
- **更新频率**: 每日自动更新

---

## ⚠️ 当前限制

1. **预测准确率**: 基线模型，准确率待提升
2. **数据覆盖**: 主要是欧洲五大联赛
3. **实时性**: 数据有延迟（API限制）
4. **语言**: 仅支持中文+英文混合

---

## 🛠️ 开发

### 添加新功能

1. **新的工具**: 在 `src/agent/tools/` 添加
2. **新的分析**: 在 `src/ml/` 添加模型
3. **新的数据源**: 在 `src/data_pipeline/` 添加

### 代码规范

- 遵循 PEP 8
- 使用 Type Hints
- 添加 Docstring
- 异步优先 (`async/await`)

---

## 📝 文档

- [测试指南](docs/TESTING_GUIDE.md)
- [聊天使用指南](CHAT_GUIDE.md)
- [数据质量报告](docs/数据真实性修复报告.md)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License

---

## 💡 下一步计划

### 短期（2周）
- [ ] 优化预测输出格式
- [ ] 添加更多分析维度
- [ ] 简单的Web界面

### 中期（2个月）
- [ ] 提升预测准确率
- [ ] 用户系统
- [ ] 付费会员功能

### 长期（6个月）
- [ ] 移动App
- [ ] 实时比分推送
- [ ] 社区功能

---

**有问题？** 

启动聊天界面直接问AI吧：
```bash
python scripts/chat_simple.py
```
