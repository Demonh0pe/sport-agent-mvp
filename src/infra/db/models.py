"""数据库实体定义 v2.0：全域数据底座 (赛事 + 用户 + 资讯)。"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, CheckConstraint, Text, Float
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

# ===========================
# 1. 赛事数据域 (Core Domain)
# 对应文档: 2.1 实体关系模型设计
# ===========================
class League(Base):
    __tablename__ = "leagues"
    league_id = Column(String, primary_key=True, index=True)
    league_name = Column(String, nullable=False)
    country = Column(String)
    level = Column(Integer, default=1)
    teams = relationship("Team", back_populates="league")

class Team(Base):
    __tablename__ = "teams"
    team_id = Column(String, primary_key=True, index=True)
    team_name = Column(String, nullable=False)
    league_id = Column(String, ForeignKey("leagues.league_id"))
    league = relationship("League", back_populates="teams")

class Match(Base):
    __tablename__ = "matches"
    match_id = Column(String, primary_key=True, index=True)
    league_id = Column(String, ForeignKey("leagues.league_id"))
    home_team_id = Column(String, ForeignKey("teams.team_id"), nullable=False)
    away_team_id = Column(String, ForeignKey("teams.team_id"), nullable=False)
    match_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="FIXTURE")
    
    # 基础比分
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    
    # [重要] 补回丢失的关键字段：结果 (H/D/A)
    result = Column(String(1), nullable=True) 
    
    # 关键升级：存储 AI 分析后的比赛标签
    tags = Column(JSON, nullable=True) 
    
    # 关系定义（关键：用于查询时预加载）
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    league = relationship("League")
    
    # [重要] 补回严谨性约束 (数据质量门禁)
    __table_args__ = (
        CheckConstraint('home_score >= 0', name='check_home_pos'),
        CheckConstraint('away_score >= 0', name='check_away_pos'),
        CheckConstraint('home_team_id != away_team_id', name='check_diff_teams'),
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Standing(Base):
    """积分榜表"""
    __tablename__ = "standings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String, ForeignKey("leagues.league_id"), index=True)
    team_id = Column(String, ForeignKey("teams.team_id"), index=True)
    season = Column(String, index=True)
    team_name = Column(String, nullable=False)  # 冗余字段，方便查询
    
    # 排名信息
    position = Column(Integer, nullable=False)
    played_games = Column(Integer, default=0)
    won = Column(Integer, default=0)
    draw = Column(Integer, default=0)
    lost = Column(Integer, default=0)
    
    # 进球数据
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_difference = Column(Integer, default=0)
    
    # 积分
    points = Column(Integer, default=0)
    
    # 关系定义
    team = relationship("Team")
    league = relationship("League")
    
    # 时间戳
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint('points >= 0', name='check_points_positive'),
        CheckConstraint('played_games >= 0', name='check_games_positive'),
    )

# ===========================
# 2. 用户画像域 (User Domain)
# ===========================
class User(Base):
    """用户表：存储画像与偏好"""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False)
    
    # 核心画像字段
    profile = Column(JSON, default={})
    
    # 行为统计
    activity_score = Column(Float, default=0.0) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserInteraction(Base):
    """用户行为表"""
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    
    target_id = Column(String, index=True) 
    target_type = Column(String) # 'match' | 'news'
    action_type = Column(String, nullable=False)
    weight = Column(Float, default=1.0)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# ===========================
# 3. 智能资讯域 (Content Domain)
# ===========================
class News(Base):
    """资讯表"""
    __tablename__ = "news"
    
    news_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    raw_content = Column(Text)
    summary = Column(Text)
    related_entities = Column(JSON)
    sentiment_score = Column(Float)
    publish_time = Column(DateTime(timezone=True))
    source = Column(String)