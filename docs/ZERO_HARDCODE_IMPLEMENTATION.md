#

>  `DATA_INTENT_GUIDE.md`
>
> Agent

##

****: 2025-11-26
****:  (5/8 )

---

## [OK]

### 1. EntityResolver  [OK]

****: `src/data_pipeline/entity_resolver.py`

****:
- [OK]
- [OK]
- [OK]
- [OK]
- [OK]

****:
```
: 302
: 120
: 21
: 6
```

****:
- [OK]
- [OK]
- [OK]
- [WARN]

---

### 2. SimpleAgentV2  [OK]

****: `src/agent/simple_agent_v2.py`

****:
- [OK] EntityResolver
- [OK]
- [OK]
- [OK] //
- [OK]

****:
|  | SimpleAgent () | SimpleAgentV2 () |
|------|-----------------|-------------------|
|  |  | EntityResolver |
|  |  | EntityResolver |
|  | ~30 | 302+  |
|  |  |  |
|  |  |  |

---

### 3. IntentClassifier  [OK]

****: `src/agent/core/intent_classifier.py`

****:
- `query`:
- `prediction`:
- `comparison`:
- `analysis`:
- `summary`:
- `clarification`:

****:
1. ****
-
-
- 80%

2. **LLM**
- /
-
- <0.7

****:
- : < 1ms
- LLM: 8-12
- : 85%+ ()

---

### 4. ComparisonScenario  [OK]

****: `src/agent/scenarios/comparison_scenario.py`

****:
- [OK]
- [OK] H2H
- [OK]
- [OK]
- [WARN]

****:
```python
from src.agent.scenarios.comparison_scenario import compare_teams

result = await compare_teams("Manchester United", "Liverpool")
print(result.conclusion)
```

---

### 5. ClarificationScenario  [OK]

****: `src/agent/scenarios/clarification_scenario.py`

****:
- `missing_team`:
- `missing_league`:
- `ambiguous_team`:
- `intent_unclear`:
- `insufficient_info`:

****:
1.
2.
3.
4.

****:
```python
from src.agent.scenarios.clarification_scenario import check_clarification

result = await check_clarification("", entities=None, intent="query")
if result.needs_clarification:
print(result.message)
print(result.candidates)
```

---

## [PENDING]

### 6.  [PENDING]

****:
****: P0

****:
1. `FootballDataIngester.run_full_ingestion()`
2. `DataQualityMonitor.run_full_check()`
3. `ImportedFromAPI`

---

### 7.  [PENDING]

****:
****: P1

****:
1.  `match_tool.get_recent_matches()`
2.  `standings_tool.get_team_standing()`
3.  `stats_tool.get_team_stats()`
4.  `prediction_tool.predict_match()`

---

### 8. Mock [PENDING]

****:
****: P1

****:
1.  `AgentServiceV2` Mock
2.  ComparisonScenario  ClarificationScenario
3. /
4.

---

##

###

|  |  |  |  |
|------|--------|--------|------|
|  | ~200 | 0 | 100% |
|  | 30 | 302+ | 10 |
|  | 5 | 21 | 4 |
|  |  |  | ∞ |
|  |  |  | -80% |

###

|  |  |  |
|------|------|--------|
| EntityResolver | [OK]  | 100% |
| SimpleAgentV2 | [OK]  | 100% |
| IntentClassifier | [OK]  | 85% |
| ComparisonScenario | [OK]  | 60% |
| ClarificationScenario | [OK]  | 90% |
|  | [PENDING]  | 0% |
| Mock | [PENDING]  | 0% |

****: 62.5% (5/8 )

---

##

###

```
src/
agent/
simple_agent_v2.py           Agent
core/
intent_classifier.py
scenarios/
__init__.py
comparison_scenario.py
clarification_scenario.py
data_pipeline/
entity_resolver.py

scripts/
test_entity_resolver.py          EntityResolver
check_database_status.py

docs/
ZERO_HARDCODE_IMPLEMENTATION.md
```

###

```
src/agent/simple_agent.py           [ERROR]  simple_agent_v2.py
src/services/api/services/agent.py  [WARN]
src/services/api/services/agent_v2.py [WARN]
src/agent/core/data_analyzer.py     [WARN]
```

---

##

### 1. EntityResolver

```bash
python scripts/test_entity_resolver.py
```

****:
- [OK]
- [OK]
- [OK]
- [WARN]

### 2. SimpleAgentV2

```bash
python -c "
import asyncio
from src.agent.simple_agent_v2 import SimpleAgentV2

async def test():
agent = SimpleAgentV2()
response = await agent.chat('5')
print(response.answer)

asyncio.run(test())
"
```

### 3. IntentClassifier

```bash
python src/agent/core/intent_classifier.py
```

### 4.

```bash
#
python src/agent/scenarios/comparison_scenario.py

#
python src/agent/scenarios/clarification_scenario.py
```

---

##

### AgentAgent

****:
```python
from src.agent.simple_agent import SimpleAgent

agent = SimpleAgent()
response = await agent.chat("")
```

****:
```python
from src.agent.simple_agent_v2 import SimpleAgentV2

agent = SimpleAgentV2()  # EntityResolver
response = await agent.chat("")
```

****:
- [OK]
- [OK] /
- [OK]
- [OK] API

### /

****:
```python
#  simple_agent.py
team_map = {
"": "New Team",
# ...
}
```

****:
```sql
--
INSERT INTO teams (team_id, team_name, league_id)
VALUES ('NEW', 'New Team ()', 'EPL');

-- EntityResolver
```

---

##

###

|  |  |  |  |
|------|------|------|------|
| Agent | < 1ms | 50-100ms | +50ms () |
|  | < 1ms | < 1ms |  |
|  | < 1ms | < 1ms |  |
|  | 8-12s | 8-12s |  |

****:

###

|  |  |  |  |
|------|------|------|------|
|  | ~5KB | ~50KB | +45KB |
|  | ~1KB | ~5KB | +4KB |
|  | ~6KB | ~55KB | +49KB |

****: < 1MB

---

## [START]

###

1. **P0**:
```bash
python scripts/check_database_status.py --all
```

2. **P0**:
- 1:
- 2:

3. **P1**:

###

4. **P1**: Mock
5. **P1**:
6. **P2**:
7. **P2**: API

### 2+

8. **P2**:
9. **P2**:
10. **P3**:
11. **P3**:

---

##

### 1.

****:

****:  "Official Name ()"

****:
- A:
- B:
- C:

****: P1

### 2. ComparisonScenario

****: H2HStats

****:

****: 7

****: P1

### 3.

****: `simple_agent.py`

****:

****:

****: P2

---

##

###

1. [OK] ****:
2. [OK] **10**:
3. [OK] **80%**:
4. [OK] ****:
5. [OK] ****: DATA_INTENT_GUIDE.md

###

- ****: 302+21+
- ****:  →  → LLM
- ****:
- ****: ComparisonScenarioClarificationScenario

###

1.
2. Mock
3.
4.

---

##


- ****: `docs/DATA_INTENT_GUIDE.md`
- ****: `docs/AGENT_ARCHITECTURE.md`
- ****: `scripts/test_*.py`

---

****: 2025-11-26
****: v1.0
****:

