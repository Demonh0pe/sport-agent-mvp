"""
服务层配置

统一管理所有服务层的配置参数，避免硬编码
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class PredictionConfig:
    """预测服务配置"""
    
    # 基线概率（主场优势）
    INITIAL_HOME_WIN_PROB: float = 0.40
    INITIAL_DRAW_PROB: float = 0.30
    INITIAL_AWAY_WIN_PROB: float = 0.30
    
    # 调整权重
    FORM_WEIGHT: float = 0.3  # 近期状态权重
    VENUE_WEIGHT: float = 0.2  # 主客场权重
    POSITION_WEIGHT: float = 0.005  # 排名权重（每差1名）
    H2H_WEIGHT: float = 0.1  # 历史交锋权重
    
    # 调整限制
    MAX_FORM_ADJUSTMENT: float = 0.15
    MAX_VENUE_ADJUSTMENT: float = 0.20
    MAX_POSITION_ADJUSTMENT: float = 0.10
    MAX_H2H_ADJUSTMENT: float = 0.10
    
    # 赛程疲劳调整
    CONGESTION_PENALTY: float = 0.05
    CONGESTION_DRAW_BONUS: float = 0.025
    
    # 概率边界
    MIN_PROBABILITY: float = 0.05
    MAX_WIN_PROBABILITY: float = 0.90
    MAX_DRAW_PROBABILITY: float = 0.50
    
    # 历史交锋最小场次
    MIN_H2H_MATCHES: int = 3
    
    # 状态判断阈值
    GOOD_FORM_THRESHOLD: float = 0.6  # 状态出色
    POOR_FORM_THRESHOLD: float = 0.3  # 状态低迷
    EXCELLENT_HOME_THRESHOLD: float = 0.7  # 主场优异
    
    # H2H 优势判断倍数
    H2H_ADVANTAGE_MULTIPLIER: float = 1.5
    
    # 特征贡献权重
    FEATURE_WEIGHTS: Dict[str, float] = None
    
    # 数据质量评估权重
    QUALITY_WEIGHTS: Dict[str, float] = None
    
    def __post_init__(self):
        if self.FEATURE_WEIGHTS is None:
            self.FEATURE_WEIGHTS = {
                "home_recent_form": 0.3,
                "away_recent_form": 0.3,
                "home_advantage": 0.2,
                "head_to_head": 0.1,
                "schedule_density": 0.1
            }
        
        if self.QUALITY_WEIGHTS is None:
            self.QUALITY_WEIGHTS = {
                "form_missing": 0.2,
                "home_away_stats_missing": 0.1,
                "h2h_missing": 0.1
            }
    
    # 输出限制
    MAX_KEY_FACTORS: int = 5  # 最多返回的关键因素数
    
    # 模型版本
    MODEL_VERSION: str = "baseline_v1.0"


@dataclass
class StatsConfig:
    """统计服务配置"""
    
    # 默认分析场次
    DEFAULT_FORM_MATCHES: int = 5
    DEFAULT_HOME_AWAY_MATCHES: int = 10
    DEFAULT_H2H_MATCHES: int = 10
    
    # 赛程密度窗口
    DEFAULT_SCHEDULE_WINDOW_DAYS: int = 14
    CONGESTION_THRESHOLD_DAYS: float = 4.0  # 平均休息天数阈值
    MIN_MATCHES_FOR_CONGESTION: int = 3  # 判断密集最少比赛数
    
    # 积分计算
    POINTS_PER_WIN: int = 3
    POINTS_PER_DRAW: int = 1
    POINTS_PER_LOSS: int = 0


@dataclass
class DataConfig:
    """数据服务配置"""
    
    # 查询限制
    DEFAULT_MATCH_LIMIT: int = 50
    MAX_MATCH_LIMIT: int = 200
    
    # 实体解析
    DEFAULT_FUZZY_THRESHOLD: float = 0.7
    RELAXED_FUZZY_THRESHOLD: float = 0.6
    
    # 积分榜显示数量
    DEFAULT_STANDINGS_DISPLAY: int = 10


@dataclass
class AgentConfig:
    """Agent 配置"""
    
    # LangChain Agent 执行参数
    MAX_ITERATIONS: int = 5
    MAX_EXPERT_ITERATIONS: int = 3
    
    # 超时设置（秒）
    SUPERVISOR_TIMEOUT: int = 30
    EXPERT_TIMEOUT: int = 10
    
    # 内存设置
    ENABLE_MEMORY: bool = True
    MAX_CONVERSATION_HISTORY: int = 10
    
    # 输出截断
    MAX_OUTPUT_SNIPPET_LENGTH: int = 200


# 全局配置实例
prediction_config = PredictionConfig()
stats_config = StatsConfig()
data_config = DataConfig()
agent_config = AgentConfig()

