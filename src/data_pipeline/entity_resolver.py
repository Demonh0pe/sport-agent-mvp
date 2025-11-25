"""
实体对齐服务 (Entity Resolution Service)
负责将外部 API 的球队/联赛名称映射到内部标准 ID。

设计理念：
1. 多策略匹配：精确匹配 -> 别名匹配 -> 模糊匹配
2. 数据库驱动：从 team_aliases 表读取映射关系
3. 可扩展：支持新数据源的对齐规则
"""
import logging
from typing import Optional, Dict
from sqlalchemy import select
from difflib import SequenceMatcher

from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Team

logger = logging.getLogger(__name__)


class EntityResolver:
    """实体对齐解析器"""
    
    def __init__(self):
        self._team_cache: Dict[str, str] = {}  # 别名 -> team_id 缓存
        self._initialized = False
    
    async def initialize(self):
        """从数据库加载所有球队信息到缓存"""
        if self._initialized:
            return
            
        async with AsyncSessionLocal() as db:
            stmt = select(Team)
            result = await db.execute(stmt)
            teams = result.scalars().all()
            
            for team in teams:
                # 缓存官方全名
                self._team_cache[team.team_name.lower()] = team.team_id
                
                # 缓存常见别名（从 team_name 中提取）
                # 例如："Manchester United (曼联)" -> ["manchester united", "曼联"]
                if "(" in team.team_name:
                    base_name = team.team_name.split("(")[0].strip()
                    alias = team.team_name.split("(")[1].replace(")", "").strip()
                    self._team_cache[base_name.lower()] = team.team_id
                    self._team_cache[alias.lower()] = team.team_id
                
        self._initialized = True
        logger.info(f"EntityResolver 初始化完成，加载了 {len(self._team_cache)} 条映射关系")
    
    async def resolve_team(
        self, 
        external_name: str,
        source: str = "football-data.org",
        fuzzy_threshold: float = 0.85
    ) -> Optional[str]:
        """
        解析球队名称到内部 ID
        
        Args:
            external_name: 外部 API 的球队名称
            source: 数据源标识
            fuzzy_threshold: 模糊匹配阈值 (0-1)
            
        Returns:
            team_id 或 None（如果无法匹配）
        """
        if not self._initialized:
            await self.initialize()
        
        # 策略 1: 精确匹配
        external_lower = external_name.lower().strip()
        if external_lower in self._team_cache:
            return self._team_cache[external_lower]
        
        # 策略 2: 去除后缀匹配 (如 "Manchester United FC" -> "Manchester United")
        cleaned_name = external_name.replace(" FC", "").replace(" CF", "").strip().lower()
        if cleaned_name in self._team_cache:
            return self._team_cache[cleaned_name]
        
        # 策略 3: 模糊匹配（相似度 > 阈值）
        best_match = None
        best_score = 0.0
        
        for cached_name, team_id in self._team_cache.items():
            score = SequenceMatcher(None, external_lower, cached_name).ratio()
            if score > best_score:
                best_score = score
                best_match = team_id
        
        if best_score >= fuzzy_threshold:
            logger.info(
                f"模糊匹配成功: '{external_name}' -> {best_match} "
                f"(相似度: {best_score:.2%})"
            )
            return best_match
        
        # 策略 4: 失败记录（用于后续人工标注）
        logger.warning(
            f"无法解析球队名称: '{external_name}' (来源: {source}), "
            f"最佳匹配: {best_match} (相似度: {best_score:.2%})"
        )
        return None
    
    async def resolve_league(
        self, 
        external_code: str,
        source: str = "football-data.org"
    ) -> Optional[str]:
        """
        解析联赛代码到内部 ID
        
        Args:
            external_code: 外部 API 的联赛代码 (如 "PL", "BL1")
            source: 数据源标识
            
        Returns:
            league_id 或 None
        """
        # 映射表：外部代码 -> 数据库联赛 ID
        # football-data.org 的代码映射到我们的数据库 ID
        league_mapping = {
            "PL": "EPL",      # Premier League -> EPL
            "BL1": "BL1",     # Bundesliga -> BL1
            "PD": "PD",       # La Liga -> PD
            "SA": "SA",       # Serie A -> SA
            "FL1": "FL1",     # Ligue 1 -> FL1
            "CL": "UCL",      # Champions League -> UCL
        }
        
        return league_mapping.get(external_code)


# 全局单例
entity_resolver = EntityResolver()

