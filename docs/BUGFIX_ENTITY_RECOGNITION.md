# Bug修复：EntityResolver集成问题

## 问题描述

用户在聊天时输入球队名称（如"巴黎圣日耳曼"、"马赛"、"里昂"、"FIO"）时，Agent无法识别这些球队，返回"暂时缺乏相关数据"。

### 问题现象

```
[你]: 巴黎圣日耳曼
[Agent]: 暂时缺乏相关数据。

[你]: 马赛
[Agent]: 暂时缺乏相关数据。

[你]: 里昂  
[Agent]: 暂时缺乏相关数据。

[你]: FIO
[Agent]: 暂时缺乏相关数据。
```

## 问题根因

经过排查，发现问题出在 `src/services/api/services/agent_v2.py` 中：

1. **硬编码的球队列表**：`_extract_team_name()` 和 `_extract_two_teams()` 方法使用了硬编码的球队列表，只包含少数几个英超和德甲球队，不包含法甲和意甲球队。

2. **未使用EntityResolver**：虽然项目中已经有了 `EntityResolver` 组件（负责从数据库动态加载所有球队并进行智能匹配），但 `agent_v2.py` 并未集成使用它。

3. **代码中的TODO注释**：在原代码第444行有注释 `TODO: 后续使用 EntityResolver 替换`，但一直未实现。

## 修复方案

### 1. 导入EntityResolver

```python
# 实体解析器
from src.data_pipeline.entity_resolver import entity_resolver
```

### 2. 初始化EntityResolver

在 `AgentServiceV2.__init__()` 中添加：

```python
self._entity_resolver = entity_resolver
self._entity_resolver_initialized = False
```

并添加初始化方法：

```python
async def _ensure_entity_resolver_initialized(self):
    """确保EntityResolver已初始化"""
    if not self._entity_resolver_initialized:
        await self._entity_resolver.initialize()
        self._entity_resolver_initialized = True
```

### 3. 重写球队提取方法

将 `_extract_team_name()` 和 `_extract_two_teams()` 改为异步方法，使用EntityResolver进行智能匹配：

**主要改进：**
- 使用EntityResolver动态查询数据库中的所有球队
- 支持中文名、英文名、缩写等多种别名
- 使用模糊匹配（阈值0.6），提高识别率
- 自动清理输入中的引号和特殊字符
- 添加详细日志便于调试

### 4. 调整调用处

在 `_execute_real_tool()` 方法中，将所有对 `_extract_team_name()` 和 `_extract_two_teams()` 的调用改为 `await` 异步调用。

## 修复效果

修复后，所有球队名称都能正确识别：

```
[你]: 巴黎圣日耳曼
[Agent]: 根据巴黎圣日耳曼近五场比赛记录，我们可以观察到以下几个关键点...

[你]: 马赛
[Agent]: 根据马赛近五场比赛的记录：...

[你]: 里昂
[Agent]: 根据提供的里昂 (LYO) 近五场比赛记录分析：...

[你]: FIO
[Agent]: 根据ACF Fiorentina（佛罗伦萨）FIO近5场比赛的记录分析如下：...
```

## 技术细节

### EntityResolver的优势

1. **零硬编码**：所有球队映射关系从数据库动态加载
2. **智能别名生成**：自动生成多种别名（中文名、英文名、缩写、前后缀变体）
3. **模糊匹配**：支持相似度匹配，容错性强
4. **可扩展**：新增球队时无需修改代码

### 识别策略

```python
async def _extract_team_name(self, query: str) -> str:
    # 1. 清理输入（去除引号、空格）
    query = query.strip().strip("'\"")
    
    # 2. 分词（按空格和标点分割）
    words = re.split(r'[\s,，、。！？：；]+', query)
    
    # 3. 逐词匹配
    for word in words:
        word = word.strip().strip("'\"")
        if len(word) < 2:
            continue
            
        # 4. 使用EntityResolver匹配（阈值0.6）
        team_id = await self._entity_resolver.resolve_team(
            word, source="agent_v2", fuzzy_threshold=0.6
        )
        
        if team_id:
            team_info = await self._entity_resolver.get_team_info(team_id)
            return team_info["name"]
    
    return ""
```

## 相关文件

- `src/services/api/services/agent_v2.py` - 主要修复文件
- `src/data_pipeline/entity_resolver.py` - EntityResolver实现
- `requirements.txt` - 添加了 `jinja2>=3.1` 依赖

## 验证方法

运行聊天脚本进行测试：

```bash
python3 scripts/chat_simple.py
```

测试用例：
- 输入法甲球队：巴黎圣日耳曼、马赛、里昂、摩纳哥
- 输入意甲球队：FIO、尤文、国米、AC米兰
- 输入其他联赛球队：曼联、皇马、拜仁

## 后续优化建议

1. **提高匹配精度**：可以考虑使用更先进的语义匹配算法
2. **支持上下文**：对于"对比"场景，可以更智能地识别两个球队
3. **错误提示优化**：当无法识别时，提供候选球队建议
4. **性能优化**：EntityResolver可以实现预加载缓存

## 修复时间

- 发现问题：2025-11-26
- 完成修复：2025-11-26
- 修复人员：AI Assistant

