#

>

##

1. ****:
2. ****: API
3. ****:
4. ****:

---

##

###

|  |  |  |  |  |
|------|------|----------|------|--------|
| **Llama-3-8B** | 8B | 8GB |  |  |
| **Qwen-7B** | 7B | 7GB |  |  |
| **ChatGLM3-6B** | 6B | 6GB |  |  |
| **Mistral-7B** | 7B | 7GB |  |  |
| **DeepSeek-Coder** | 6.7B | 7GB |  |  |

****: Qwen-7B  Llama-3-8B

---

## [START]

### A: Ollama

#### 1. Ollama

```bash
# macOS
brew install ollama

#
# https://ollama.ai/download
```

#### 2.

```bash
# Qwen
ollama pull qwen:7b

#  Llama3
ollama pull llama3:8b

#  ChatGLM
ollama pull chatglm3:6b
```

#### 3. Ollama

```bash
#
ollama serve
```

#### 4.

`.env`

```bash
#
LLM_PROVIDER=ollama
LLM_MODEL=qwen:7b
LLM_BASE_URL=http://localhost:11434
```

#### 5. LLM

```python
# src/shared/llm_client.py
from openai import AsyncOpenAI

settings = get_settings()

# Ollama
if settings.llm.provider == "ollama":
llm_client = AsyncOpenAI(
base_url="http://localhost:11434/v1",  # OllamaOpenAI API
api_key="ollama",  #
)
else:
# DeepSeek
llm_client = AsyncOpenAI(...)
```

---

### B: LM StudioGUI

#### 1. LM Studio

https://lmstudio.ai/

#### 2.

LM Studio
- Qwen/Qwen-7B-Chat
- meta-llama/Llama-3-8B
- THUDM/ChatGLM3-6B

#### 3.

LM Studio
1.
2.  "Start Server"
3. : 1234

#### 4.

```bash
LLM_PROVIDER=lmstudio
LLM_MODEL=qwen-7b
LLM_BASE_URL=http://localhost:1234/v1
```

---

### C: vLLM

GPU

#### 1. vLLM

```bash
pip install vllm
```

#### 2.

```bash
python -m vllm.entrypoints.openai.api_server \
--model Qwen/Qwen-7B-Chat \
--port 8000
```

#### 3.

```bash
LLM_PROVIDER=vllm
LLM_MODEL=Qwen/Qwen-7B-Chat
LLM_BASE_URL=http://localhost:8000/v1
```

---

##

### 1.

`config/service.yaml`:

```yaml
llm:
# : openai, deepseek, ollama, lmstudio, vllm
provider: ${LLM_PROVIDER:ollama}

#
model: ${LLM_MODEL:qwen:7b}

# API
api_key: ${LLM_API_KEY:ollama}
base_url: ${LLM_BASE_URL:http://localhost:11434/v1}

#
temperature: 0.7
max_tokens: 2000
```

### 2. LLM

`src/shared/llm_client.py`:

```python
"""
LLM -


- OpenAI
- DeepSeek
- Ollama ()
- LM Studio ()
- vLLM ()


"""

from openai import AsyncOpenAI
from src.shared.config import get_settings
import logging

logger = logging.getLogger(__name__)


class LLMClient:
"""
LLM

OpenAI
- OpenAI
- DeepSeek
- Ollama
- LM Studio
- vLLM
"""

def __init__(self):
settings = get_settings()

provider = settings.llm.provider.lower()

#
if provider in ["ollama", "lmstudio", "vllm"]:
# OpenAI
self.client = AsyncOpenAI(
base_url=settings.llm.base_url,
api_key="local-llm",  # key
)
logger.info(f"LLM: {provider} @ {settings.llm.base_url}")

elif provider == "deepseek":
# DeepSeek
self.client = AsyncOpenAI(
api_key=settings.llm.api_key,
base_url="https://api.deepseek.com",
)
logger.info("DeepSeek API")

elif provider == "openai":
# OpenAI
self.client = AsyncOpenAI(
api_key=settings.llm.api_key,
)
logger.info("OpenAI API")

else:
raise ValueError(f"LLM: {provider}")

self.model = settings.llm.model
self.temperature = settings.llm.temperature
self.max_tokens = settings.llm.max_tokens

async def generate(self, prompt: str, **kwargs) -> str:
"""


Args:
prompt:
**kwargs: temperature, max_tokens

Returns:

"""
try:
response = await self.client.chat.completions.create(
model=self.model,
messages=[{"role": "user", "content": prompt}],
temperature=kwargs.get("temperature", self.temperature),
max_tokens=kwargs.get("max_tokens", self.max_tokens),
)

return response.choices[0].message.content

except Exception as e:
logger.error(f"LLM: {e}")
raise


#
llm_client = LLMClient()
```

### 3.

`.env`:

```bash
# LLM
LLM_PROVIDER=ollama  # : openai, deepseek, ollama, lmstudio, vllm
LLM_MODEL=qwen:7b
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=local-llm  # key
```

---

##

###

|  | token |  (100 tokens) |  |
|------|------------|-------------------|--------|
| **DeepSeek API** | 1-2s | 3-5s |  |
| **Ollama (CPU)** | 2-3s | 5-8s |  |
| **Ollama (GPU)** | 0.5s | 1-2s |  |
| **vLLM (GPU)** | 0.3s | 0.8-1.5s |  |
| **LM Studio** | 2-3s | 5-8s |  |

###

|  |  |  |  |
|------|----------|----------|----------|
| Qwen-7B | FP16 | 14GB | RTX 3090 |
| Qwen-7B | INT8 | 7GB | RTX 3060 |
| Qwen-7B | INT4 | 4GB | Mac M1 |
| Llama3-8B | FP16 | 16GB | RTX 3090 |
| Llama3-8B | INT4 | 4.5GB | Mac M1 |

****: INT4<5%75%

---

##

### 1.

```python
from src.shared.llm_client import llm_client

#
response = await llm_client.generate("")
print(response)
```

### 2. IntentClassifier

```python
from src.agent.core.intent_classifier import classify_intent

# LLM
result = await classify_intent("")
print(result.intent)  # prediction
```

### 3.

```bash
# Ollama
export LLM_PROVIDER=ollama
export LLM_MODEL=qwen:7b

# DeepSeek
export LLM_PROVIDER=deepseek
export LLM_MODEL=deepseek-chat

# OpenAI
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4
```

---

##

###

1. ****:
2. **API**:
3. ****:
4. ****:

###

|  |  | 1 |
|------|-------------|------------------|
| OpenAI GPT-4 | $0.01-0.03 | $100-300 |
| DeepSeek | $0.001-0.002 | $10-20 |
| **** | **$0** | **$0** |

---

##

### 1: Ollama

```bash
# Ollama
curl http://localhost:11434/api/tags

# Ollama
ollama serve
```

### 2:

```bash
#
export OLLAMA_MODELS=/path/to/models
ollama pull qwen:7b
```

### 3:

```bash
#
ollama pull qwen:7b-q4_0  # INT4
```

### 4: GPU

```bash
# GPU
nvidia-smi  # Linux
#
system_profiler SPDisplaysDataType  # macOS

# OllamaGPU
```

---

##

###

- **Ollama**: https://ollama.ai/library
- **Hugging Face**: https://huggingface.co/models
- **ModelScope**: https://modelscope.cn/models

###

- **Ollama**: https://github.com/jmorganca/ollama
- **LM Studio**: https://lmstudio.ai/docs
- **vLLM**: https://docs.vllm.ai/

---

##

### 1.

- Ollama + INT4
-

### 2.

- vLLM + GPU
-

### 3.

```python
# LLM
if use_rules_first:
result = rule_based_classify(query)
if result.confidence < 0.7:
result = llm_based_classify(query)  # LLM
```

### 4.

```python
# LLM
from functools import lru_cache

@lru_cache(maxsize=1000)
async def cached_generate(prompt: str):
return await llm_client.generate(prompt)
```

---

## [OK]

- [ ] OllamaLM Studio
- [ ] Qwen/Llama3
- [ ]  `.env`
- [ ]  `llm_client.py`
- [ ] IntentClassifier
- [ ] Agent
- [ ]
- [ ]

---

## [START]

1. ****: Ollama / LM Studio / vLLM
2. ****: Qwen-7B
3. ****:  `.env`
4. ****: IntentClassifier
5. ****:

---

****: ********

