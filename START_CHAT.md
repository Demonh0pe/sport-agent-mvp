# 🚀 快速启动聊天界面

**最后更新**: 2025-11-25

---

## ⚡ 立即开始

### 1️⃣ 简洁模式（推荐新手）

```bash
cd /Users/dylan/Desktop/sport\ agent\ mvp
source .venv/bin/activate
python scripts/chat_simple.py
```

**特点**: 极简界面，只显示问答

---

### 2️⃣ 标准模式（推荐日常使用）⭐

```bash
cd /Users/dylan/Desktop/sport\ agent\ mvp
source .venv/bin/activate
python scripts/chat_with_agent.py
```

**特点**: 显示工具调用、耗时统计，支持 help/clear 命令

---

### 3️⃣ 调试模式（开发调试）

```bash
cd /Users/dylan/Desktop/sport\ agent\ mvp
source .venv/bin/activate
python scripts/chat_debug.py
```

**特点**: 显示完整日志、执行计划、工具输入输出

---

## 💬 示例对话

启动后直接输入问题：

```
💬 你的问题: 曼联最近5场比赛的战绩如何

🤖 Agent: 根据提供的数据，曼联最近5场比赛的战绩为：
- 2025-11-24: 曼联 vs 埃弗顿 (0:1) 负
- 2025-11-08: 托特纳姆 vs 曼联 (2:2) 平
- 2025-11-01: 诺丁汉 vs 曼联 (2:2) 平
- 2025-10-25: 曼联 vs 布莱顿 (4:2) 胜
- 2025-10-19: 利物浦 vs 曼联 (1:2) 胜

总战绩: 2胜2平1负
```

---

## 🎯 试试这些问题

### 比赛预测
- 曼联对利物浦，谁会赢？
- 预测一下曼城和阿森纳的比赛
- 皇马vs巴萨，哪个队会获胜

### 战绩查询
- 曼联最近5场比赛的战绩如何
- 利物浦近期表现怎么样
- 阿森纳最近胜率如何

### 排名查询
- 利物浦在英超中处于什么地位
- 曼城现在排名第几

---

## 📋 命令说明

| 命令 | 说明 |
|------|------|
| 直接输入问题 | 提问 |
| `exit` / `quit` / `q` | 退出 |
| `help` | 查看示例（标准模式） |
| `clear` | 清屏（标准模式） |
| `Ctrl+C` | 中断 |

---

## ✅ 验证系统状态

运行前可以先验证数据质量：

```bash
python scripts/quick_verify_data.py
```

应该看到：
```
✅✅✅ 数据验证通过！所有数据均真实可靠 ✅✅✅
```

---

## 🐛 常见问题

### Q: 提示 "cannot import name 'agent_service'"

**A**: 已修复！确保使用最新版本的脚本。

### Q: 连接数据库失败

**A**: 启动数据库
```bash
docker-compose up -d postgres
```

### Q: 响应很慢

**A**: 首次查询需要加载模型（10-20秒），之后会快很多。

---

## 📚 详细文档

查看完整使用指南：
```bash
cat CHAT_GUIDE.md
```

---

**现在就开始对话吧！** 🚀

```bash
python scripts/chat_with_agent.py
```

