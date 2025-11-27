"""
实体对齐服务 (Entity Resolution Service)
负责将外部 API 的球队/联赛名称映射到内部标准 ID。

设计理念：
1. 多策略匹配：精确匹配 -> 别名匹配 -> 模糊匹配
2. 数据库驱动：从数据库动态加载所有实体
3. 可扩展：支持新数据源的对齐规则
4. 零硬编码：所有映射关系来自数据库，不在代码中硬编码
"""
import logging
from typing import Optional, Dict, List
from sqlalchemy import select, or_
from difflib import SequenceMatcher

from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Team, League

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    实体对齐解析器
    
    功能：
    1. 动态从数据库加载所有球队和联赛
    2. 自动生成多种别名（全名、简称、中文名、缩写）
    3. 支持精确匹配、模糊匹配
    4. 提供搜索和建议功能（用于澄清场景）
    
    零硬编码设计：所有映射关系从数据库动态加载
    """
    
    def __init__(self):
        self._team_cache: Dict[str, str] = {}  # 别名 -> team_id 缓存
        self._team_info: Dict[str, Dict] = {}  # team_id -> {name, league, ...}
        self._league_cache: Dict[str, str] = {}  # 别名 -> league_id 缓存
        self._league_info: Dict[str, Dict] = {}  # league_id -> {name, country, ...}
        self._initialized = False
    
    async def initialize(self):
        """从数据库加载所有实体信息到缓存"""
        if self._initialized:
            return
            
        async with AsyncSessionLocal() as db:
            # 加载所有球队
            stmt = select(Team)
            result = await db.execute(stmt)
            teams = result.scalars().all()
            
            for team in teams:
                # 保存球队完整信息
                self._team_info[team.team_id] = {
                    "name": team.team_name,
                    "id": team.team_id,
                    "league_id": team.league_id,
                }
                
                # 生成所有可能的别名
                aliases = self._generate_team_aliases(team.team_name, team.team_id)
                for alias in aliases:
                    self._team_cache[alias.lower()] = team.team_id
            
            # 加载所有联赛
            stmt = select(League)
            result = await db.execute(stmt)
            leagues = result.scalars().all()
            
            for league in leagues:
                # 保存联赛完整信息
                self._league_info[league.league_id] = {
                    "id": league.league_id,
                    "name": league.league_name,
                    "country": league.country,
                    "level": league.level,
                }
                
                # 生成所有可能的别名
                aliases = self._generate_league_aliases(league.league_name, league.league_id)
                for alias in aliases:
                    self._league_cache[alias.lower()] = league.league_id
                
        self._initialized = True
        logger.info(
            f"EntityResolver 初始化完成：{len(self._team_cache)} 条球队映射，"
            f"{len(self._league_cache)} 条联赛映射"
        )
    
    def _generate_team_aliases(self, team_name: str, team_id: str) -> List[str]:
        """
        从球队名称自动生成所有可能的别名
        
        例如：
        - "Manchester United (曼联)" -> ["Manchester United", "曼联", "Man Utd", "MUN"]
        - "FC Barcelona" -> ["FC Barcelona", "Barcelona", "Barca", "FCB"]
        - "Real Sociedad de Fútbol" -> ["Real Sociedad de Fútbol", "Real Sociedad", "RSO"]
        """
        aliases = []
        working_name = team_name
        
        # 1. 官方全名
        aliases.append(team_name)
        
        # 2. 提取中文别名（括号内）
        if "(" in team_name and ")" in team_name:
            base_name = team_name.split("(")[0].strip()
            chinese_name = team_name.split("(")[1].replace(")", "").strip()
            aliases.append(base_name)
            aliases.append(chinese_name)
            working_name = base_name  # 使用英文名进行后续处理
        
        # 3. 去除常见后缀（扩展列表）
        suffixes_to_remove = [
            " FC", " CF", " AFC", " SC", " AC", " AS", " SV", " TSG",
            " United", " City", " Town", " Wanderers", " Rovers",
            " Calcio", " BC", " OSC", " SCO", 
            " de Fútbol", " Balompié", " de Vigo",  # 西班牙语
            " e Benfica", " de Marseille",  # 葡萄牙/法语
            " 1909", " 1899", " 1901", " 29",  # 年份后缀
        ]
        
        for suffix in suffixes_to_remove:
            if working_name.endswith(suffix):
                short_name = working_name.replace(suffix, "").strip()
                aliases.append(short_name)
                # 继续从短名称中移除其他后缀
                for suffix2 in suffixes_to_remove:
                    if short_name.endswith(suffix2):
                        aliases.append(short_name.replace(suffix2, "").strip())
        
        # 4. 去除常见前缀（扩展列表）
        prefixes_to_remove = [
            "FC ", "CF ", "AFC ", "SC ", "AC ", "AS ", "SV ", "TSG ",
            "1. ", "US ", "SS ", "SSC ", "ACF ",
            "Sport Lisboa ",  # 葡萄牙
            "Olympique ",  # 法国
        ]
        
        for prefix in prefixes_to_remove:
            if working_name.startswith(prefix):
                short_name = working_name.replace(prefix, "", 1).strip()
                aliases.append(short_name)
                # 继续从短名称中移除其他前缀
                for prefix2 in prefixes_to_remove:
                    if short_name.startswith(prefix2):
                        aliases.append(short_name.replace(prefix2, "", 1).strip())
        
        # 5. team_id 本身（通常是缩写）
        aliases.append(team_id)
        
        # 6. 特殊处理：同时去除前缀和后缀
        # 例如 "FC Barcelona CF" -> "Barcelona"
        temp_name = working_name
        for prefix in prefixes_to_remove:
            if temp_name.startswith(prefix):
                temp_name = temp_name.replace(prefix, "", 1).strip()
        for suffix in suffixes_to_remove:
            if temp_name.endswith(suffix):
                temp_name = temp_name.replace(suffix, "").strip()
        if temp_name != working_name:
            aliases.append(temp_name)
        
        # 7. 常用中文简称映射（球迷常用叫法）
        chinese_nicknames = {
            # 西甲
            "barcelona": ["巴萨", "巴塞"],
            "real madrid": ["皇马"],
            "atletico": ["马竞", "床单军团"],
            "sevilla": ["塞维利亚"],
            "villarreal": ["黄潜", "黄色潜水艇"],
            "betis": ["贝蒂斯"],
            "sociedad": ["皇家社会", "皇社"],
            "athletic": ["毕巴", "毕尔巴鄂"],
            "valencia": ["瓦伦西亚", "蝙蝠军团"],
            "celta": ["塞尔塔"],
            # 英超
            "manchester united": ["曼联", "红魔"],
            "manchester city": ["曼城", "蓝月亮"],
            "liverpool": ["利物浦", "红军"],
            "arsenal": ["阿森纳", "枪手", "兵工厂"],
            "chelsea": ["切尔西", "蓝军"],
            "tottenham": ["热刺", "白百合"],
            "aston villa": ["维拉", "阿斯顿维拉"],
            "newcastle": ["纽卡", "纽卡斯尔", "喜鹊"],
            "west ham": ["西汉姆", "铁锤帮"],
            "brighton": ["布莱顿", "海鸥"],
            "everton": ["埃弗顿", "太妃糖"],
            "crystal palace": ["水晶宫"],
            "wolves": ["狼队"],
            "bournemouth": ["伯恩茅斯", "樱桃"],
            "fulham": ["富勒姆"],
            "brentford": ["布伦特福德"],
            "nottingham": ["诺丁汉森林", "森林"],
            "burnley": ["伯恩利"],
            "luton": ["卢顿"],
            "sheffield": ["谢菲联"],
            # 德甲
            "bayern": ["拜仁", "南大王"],
            "dortmund": ["多特", "大黄蜂"],
            "leverkusen": ["勒沃库森", "药厂"],
            "leipzig": ["莱比锡"],
            "frankfurt": ["法兰克福"],
            "gladbach": ["门兴"],
            "wolfsburg": ["沃尔夫斯堡", "狼堡"],
            "freiburg": ["弗赖堡"],
            "hoffenheim": ["霍芬海姆"],
            "stuttgart": ["斯图加特"],
            # 意甲
            "juventus": ["尤文", "斑马军团", "老妇人"],
            "inter": ["国际米兰", "国米", "蓝黑军团"],
            "milan": ["AC米兰", "红黑军团"],
            "napoli": ["那不勒斯"],
            "roma": ["罗马", "红狼"],
            "lazio": ["拉齐奥", "蓝鹰"],
            "atalanta": ["亚特兰大"],
            "fiorentina": ["佛罗伦萨", "紫百合"],
            # 法甲
            "paris": ["巴黎", "大巴黎"],
            "marseille": ["马赛"],
            "lyon": ["里昂"],
            "monaco": ["摩纳哥"],
            "lille": ["里尔"],
            "nice": ["尼斯"],
            "lens": ["朗斯"],
            "rennes": ["雷恩"],
        }
        
        name_lower = working_name.lower()
        for key, nicknames in chinese_nicknames.items():
            if key in name_lower:
                aliases.extend(nicknames)
        
        # 去重并过滤空字符串
        return list(set(alias for alias in aliases if alias.strip()))
    
    def _generate_league_aliases(self, league_name: str, league_id: str) -> List[str]:
        """
        从联赛名称自动生成所有可能的别名
        
        例如：
        - "Premier League (英超)" -> ["Premier League", "英超", "EPL", "PL"]
        - "德国甲级联赛" -> ["德国甲级联赛", "德甲", "BL1", "Bundesliga"]
        """
        aliases = []
        
        # 1. 官方全名
        aliases.append(league_name)
        
        # 2. 联赛ID
        aliases.append(league_id)
        
        # 3. 提取中文别名
        if "(" in league_name and ")" in league_name:
            base_name = league_name.split("(")[0].strip()
            chinese_name = league_name.split("(")[1].replace(")", "").strip()
            aliases.append(base_name)
            aliases.append(chinese_name)
        
        # 4. 常见简称映射
        name_lower = league_name.lower()
        if "premier" in name_lower or "英超" in league_name:
            aliases.extend(["英超", "Premier League", "EPL", "PL"])
        elif "bundesliga" in name_lower or "德" in league_name:
            aliases.extend(["德甲", "Bundesliga", "BL1"])
        elif "liga" in name_lower and ("la" in name_lower or "西" in league_name):
            aliases.extend(["西甲", "La Liga", "PD"])
        elif "serie" in name_lower or "意" in league_name:
            aliases.extend(["意甲", "Serie A", "SA"])
        elif "ligue" in name_lower or "法" in league_name:
            aliases.extend(["法甲", "Ligue 1", "FL1"])
        elif "champions" in name_lower or "欧冠" in league_name:
            aliases.extend(["欧冠", "Champions League", "UCL", "CL"])
        
        return list(set(aliases))  # 去重
    
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
        source: str = "user_query",
        fuzzy_threshold: float = 0.85
    ) -> Optional[str]:
        """
        解析联赛名称/代码到内部 ID
        
        Args:
            external_code: 外部联赛名称或代码
            source: 数据源标识
            fuzzy_threshold: 模糊匹配阈值
            
        Returns:
            league_id 或 None
        """
        if not self._initialized:
            await self.initialize()
        
        # 策略 1: 精确匹配
        external_lower = external_code.lower().strip()
        if external_lower in self._league_cache:
            return self._league_cache[external_lower]
        
        # 策略 2: 模糊匹配
        best_match = None
        best_score = 0.0
        
        for cached_name, league_id in self._league_cache.items():
            score = SequenceMatcher(None, external_lower, cached_name).ratio()
            if score > best_score:
                best_score = score
                best_match = league_id
        
        if best_score >= fuzzy_threshold:
            logger.info(
                f"联赛模糊匹配成功: '{external_code}' -> {best_match} "
                f"(相似度: {best_score:.2%})"
            )
            return best_match
        
        logger.warning(
            f"无法解析联赛: '{external_code}' (来源: {source})"
        )
        return None
    
    async def search_teams(
        self, 
        query: str, 
        limit: int = 5,
        league_id: Optional[str] = None
    ) -> List[Dict]:
        """
        搜索球队（用于澄清场景）
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量
            league_id: 可选，限制在指定联赛
            
        Returns:
            匹配的球队列表，每项包含 {id, name, league_id, score}
        """
        if not self._initialized:
            await self.initialize()
        
        query_lower = query.lower().strip()
        results = []
        
        for team_id, info in self._team_info.items():
            # 如果指定了联赛，先过滤
            if league_id and info["league_id"] != league_id:
                continue
            
            # 计算匹配分数
            score = SequenceMatcher(None, query_lower, info["name"].lower()).ratio()
            
            if score > 0.3:  # 最低匹配阈值
                results.append({
                    "id": team_id,
                    "name": info["name"],
                    "league_id": info["league_id"],
                    "score": score
                })
        
        # 按分数排序，返回前N个
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    async def search_leagues(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Dict]:
        """
        搜索联赛（用于澄清场景）
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量
            
        Returns:
            匹配的联赛列表，每项包含 {id, name, country, score}
        """
        if not self._initialized:
            await self.initialize()
        
        query_lower = query.lower().strip()
        results = []
        
        for league_id, info in self._league_info.items():
            # 计算匹配分数
            score = SequenceMatcher(None, query_lower, info["name"].lower()).ratio()
            
            if score > 0.3:
                results.append({
                    "id": league_id,
                    "name": info["name"],
                    "country": info["country"],
                    "score": score
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    async def get_all_teams(self, league_id: Optional[str] = None) -> List[Dict]:
        """
        获取所有球队
        
        Args:
            league_id: 可选，只返回指定联赛的球队
            
        Returns:
            球队列表
        """
        if not self._initialized:
            await self.initialize()
        
        if league_id:
            return [
                info for info in self._team_info.values()
                if info["league_id"] == league_id
            ]
        return list(self._team_info.values())
    
    async def get_all_leagues(self) -> List[Dict]:
        """获取所有联赛"""
        if not self._initialized:
            await self.initialize()
        
        return list(self._league_info.values())
    
    async def get_team_info(self, team_id: str) -> Optional[Dict]:
        """获取球队详细信息"""
        if not self._initialized:
            await self.initialize()
        
        return self._team_info.get(team_id)
    
    async def get_league_info(self, league_id: str) -> Optional[Dict]:
        """获取联赛详细信息"""
        if not self._initialized:
            await self.initialize()
        
        return self._league_info.get(league_id)


# 全局单例
entity_resolver = EntityResolver()

