"""
⚠️⚠️⚠️ 警告: 此脚本已废弃！请勿使用！ ⚠️⚠️⚠️

【废弃原因】
此脚本会创建虚假测试数据，导致与真实API数据混淆，影响Agent输出的准确性。

【已知问题】
1. 使用动态时间生成数据，与真实比赛时间冲突
2. 没有明确标记为测试数据
3. 与真实API数据混合在同一数据库中

【替代方案】
1. 单元测试: 使用 Mock 数据 (src/agent/tools/mock_responses.py)
2. 集成测试: 使用独立的测试数据库
3. 开发环境: 直接使用 football-data.org API 拉取真实数据

【如需执行】
如果你确实需要运行此脚本（例如在隔离的测试环境），请:
1. 确保使用独立的测试数据库
2. 在代码中注释掉下方的 RuntimeError
3. 运行后记得清理数据

数据播种脚本 (Data Seeding Script) - DEPRECATED
作用：向数据库注入符合 v2.0 Schema 的初始测试数据。
包含：英超联赛、4支豪门球队、2场典型比赛、1个测试用户、1条相关新闻。
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

# 1. 将项目根目录加入 Python 路径，确保能导入 src 模块
sys.path.append(os.getcwd())

from sqlalchemy import select
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import League, Team, Match, User, News

async def seed_data():
    raise RuntimeError(
        "\n" + "=" * 80 + "\n"
        "❌ 此脚本已禁用！请勿在生产环境运行。\n\n"
        "【原因】会创建虚假测试数据，与真实API数据混淆。\n\n"
        "【替代方案】\n"
        "1. 单元测试: 使用 Mock 数据 (src/agent/tools/mock_responses.py)\n"
        "2. 集成测试: 使用独立的测试数据库\n"
        "3. 开发环境: 使用 scripts/ingest_football_data_v2.py 拉取真实数据\n\n"
        "详见: docs/DATA_AUTHENTICITY_AUDIT.md\n"
        + "=" * 80
    )
    
    async with AsyncSessionLocal() as db:
        print("开始执行数据播种 (Data Seeding)...")

        # --- 1. 检查是否已存在数据 (防止重复插入报错) ---
        stmt = select(League).where(League.league_id == "EPL")
        result = await db.execute(stmt)
        if result.scalars().first():
            print("检测到数据库中已有 'EPL' 数据，停止播种。")
            print("   (若需重置，请手动清空数据库表)")
            return

        # --- 2. 基础数据：联赛 ---
        print("   > 创建英超联赛...")
        epl = League(
            league_id="EPL", 
            league_name="Premier League (英超)", 
            country="England", 
            level=1
        )
        db.add(epl)
        
        # --- 3. 基础数据：球队 (中英文名，方便模糊搜索) ---
        print("   > 创建 4 支球队...")
        teams = [
            Team(team_id="MUN", team_name="Manchester United (曼联)", league_id="EPL"),
            Team(team_id="LIV", team_name="Liverpool (利物浦)", league_id="EPL"),
            Team(team_id="ARS", team_name="Arsenal (阿森纳)", league_id="EPL"),
            Team(team_id="MCI", team_name="Manchester City (曼城)", league_id="EPL"),
        ]
        db.add_all(teams)
        
        # 提交一次，确保外键关联正确
        await db.commit()
        
        # --- 4. 业务数据：比赛 ---
        print("   > 创建比赛记录...")
        
        # 场景 A: 已结束的惨败 (曼联 0:3 利物浦) - 用于测试战报生成
        match_finished = Match(
            match_id="2024_EPL_MUN_LIV",
            league_id="EPL",
            home_team_id="MUN",
            away_team_id="LIV",
            # 比赛时间：3天前
            match_date=datetime.now(timezone.utc) - timedelta(days=3),
            status="FINISHED",
            home_score=0,
            away_score=3,
            result="A",  # Away Win (客队胜)
            # 智能标签：用于未来的推荐系统召回
            tags=["Derby", "Big6", "惨败"]
        )
        
        # 场景 B: 未开始的争冠战 (阿森纳 vs 曼城) - 用于测试赛前预测
        match_fixture = Match(
            match_id="2024_EPL_ARS_MCI",
            league_id="EPL",
            home_team_id="ARS",
            away_team_id="MCI",
            # 比赛时间：4天后
            match_date=datetime.now(timezone.utc) + timedelta(days=4),
            status="FIXTURE",
            home_score=None,
            away_score=None,
            result=None,  # 未开始的比赛，无结果
            tags=["Title Race", "关键战"]
        )
        db.add_all([match_finished, match_fixture])
        
        # --- 5. 运营数据：用户画像 ---
        print("   > 创建测试用户...")
        user = User(
            user_id="test_admin",
            username="AdminUser",
            # 画像：这是曼联的死忠粉，风险偏好高
            profile={
                "favorite_teams": ["MUN"],
                "risk_preference": "high",
                "tags": ["数据控", "主队死忠"]
            },
            activity_score=100.0
        )
        db.add(user)
        
        # --- 6. 内容数据：新闻资讯 ---
        print("   > 创建相关新闻...")
        news = News(
            news_id="NEWS_001",
            title="Ten Hag under pressure",
            # 原始内容
            raw_content="Manchester United lost 0-3 to Liverpool at Old Trafford...",
            # AI 提取的摘要
            summary="曼联主场0-3惨败利物浦，中场控制力丧失，滕哈赫赛后发言引发争议，帅位岌岌可危。",
            # 关联实体：用于 RAG 检索
            related_entities=["MUN", "LIV", "Ten Hag", "Casemiro"],
            sentiment_score=-0.9, # 极度负面
            publish_time=datetime.now(timezone.utc) - timedelta(days=2),
            source="BBC Sport"
        )
        db.add(news)

        await db.commit()
        print("数据播种全部完成！")

if __name__ == "__main__":
    # 运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(seed_data())