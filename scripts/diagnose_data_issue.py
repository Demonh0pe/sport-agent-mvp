"""
数据缺失诊断工具 - 找出为什么数据没有正确摄取

用法: python scripts/diagnose_data_issue.py
"""
import asyncio
import sys
import os
import httpx
from datetime import datetime, timedelta, timezone

sys.path.append(os.getcwd())

from sqlalchemy import select, func
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import League, Team, Match
from src.shared.config import get_settings
from src.data_pipeline.entity_resolver import entity_resolver


async def check_league_configuration():
    """检查联赛配置"""
    print("\n" + "=" * 80)
    print("📋 步骤1: 检查联赛配置")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        stmt = select(League)
        result = await db.execute(stmt)
        leagues = result.scalars().all()
        
        if not leagues:
            print("❌ 数据库中没有联赛数据！")
            print("   解决方案: python scripts/seed_leagues.py")
            return False
        
        print(f"\n✅ 找到 {len(leagues)} 个联赛:")
        for league in leagues:
            print(f"   - {league.league_id:<10} {league.league_name}")
        
        # 检查PL（英超）是否存在
        pl_stmt = select(League).where(League.league_id == "PL")
        pl_result = await db.execute(pl_stmt)
        pl = pl_result.scalar_one_or_none()
        
        if not pl:
            print("\n❌ 未找到PL（英超）联赛配置！")
            print("   这可能导致英超数据为0")
            return False
        else:
            print(f"\n✅ 英超联赛配置正常: {pl.league_name} (ID: PL)")
        
        return True


async def check_teams_data():
    """检查球队数据"""
    print("\n" + "=" * 80)
    print("🏃 步骤2: 检查球队数据")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        # 统计各联赛的球队数
        stmt = select(Team.league_id, func.count()).group_by(Team.league_id)
        result = await db.execute(stmt)
        team_counts = dict(result.all())
        
        expected_teams = {
            "PL": 20,   # 英超（注意：数据库中是PL不是EPL）
            "BL1": 18,
            "PD": 20,
            "SA": 20,
            "FL1": 18,
        }
        
        print(f"\n{'联赛':<10} {'当前球队数':<12} {'预期':<10} {'状态'}")
        print("-" * 50)
        
        has_issue = False
        for league_id, expected in expected_teams.items():
            current = team_counts.get(league_id, 0)
            if current == 0:
                status = "❌ 无球队"
                has_issue = True
            elif current < expected:
                status = "⚠️  球队不足"
                has_issue = True
            else:
                status = "✅ 正常"
            
            print(f"{league_id:<10} {current:<12} {expected:<10} {status}")
        
        if has_issue:
            print("\n⚠️  发现球队数据问题，这会导致比赛数据无法匹配")
            print("   解决方案: 运行数据摄取会自动创建缺失的球队")
        
        # 检查PL（英超）的球队
        pl_stmt = select(Team).where(Team.league_id == "PL")
        pl_result = await db.execute(pl_stmt)
        pl_teams = pl_result.scalars().all()
        
        if pl_teams:
            print(f"\n✅ 英超球队列表 ({len(pl_teams)}支):")
            for team in pl_teams[:5]:
                print(f"   - {team.team_id:<10} {team.team_name}")
            if len(pl_teams) > 5:
                print(f"   ... 还有 {len(pl_teams) - 5} 支球队")
        else:
            print("\n❌ 英超没有任何球队数据！")
            print("   这是英超比赛为0的主要原因")
        
        return not has_issue


async def check_api_connection():
    """检查API连接和权限"""
    print("\n" + "=" * 80)
    print("🌐 步骤3: 检查API连接")
    print("=" * 80)
    
    settings = get_settings()
    config = settings.service.data_source.football_data_org
    
    print(f"\nAPI配置:")
    print(f"   Base URL: {config.base_url}")
    print(f"   API Key:  {'✅ 已配置' if config.api_key else '❌ 未配置'}")
    
    if not config.api_key:
        print("\n❌ API Key未配置！")
        print("   解决方案: 在 config/service.yaml 中配置 api_key")
        return False
    
    # 测试API连接
    headers = {"X-Auth-Token": config.api_key}
    
    # 测试各个联赛的API访问
    test_leagues = {
        "PL": "英超（EPL）",
        "BL1": "德甲",
        "PD": "西甲",
        "SA": "意甲",
        "FL1": "法甲"
    }
    
    print(f"\n正在测试API访问权限...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        api_issues = []
        
        for code, name in test_leagues.items():
            try:
                # 只获取1场比赛测试
                url = f"{config.base_url}/competitions/{code}/matches"
                response = await client.get(
                    url,
                    headers=headers,
                    params={"limit": 1}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    match_count = len(data.get("matches", []))
                    print(f"   ✅ {code:<6} {name:<15} - 可访问")
                elif response.status_code == 403:
                    print(f"   ❌ {code:<6} {name:<15} - 权限不足（需要付费计划）")
                    api_issues.append((code, name, "权限不足"))
                elif response.status_code == 404:
                    print(f"   ⚠️  {code:<6} {name:<15} - 联赛不存在或代码错误")
                    api_issues.append((code, name, "联赛不存在"))
                else:
                    print(f"   ⚠️  {code:<6} {name:<15} - HTTP {response.status_code}")
                    api_issues.append((code, name, f"HTTP {response.status_code}"))
                
                await asyncio.sleep(1)  # 避免限流
                
            except httpx.TimeoutException:
                print(f"   ❌ {code:<6} {name:<15} - 连接超时")
                api_issues.append((code, name, "连接超时"))
            except Exception as e:
                print(f"   ❌ {code:<6} {name:<15} - 错误: {str(e)[:30]}")
                api_issues.append((code, name, str(e)))
        
        if api_issues:
            print(f"\n⚠️  发现 {len(api_issues)} 个API访问问题")
            return False
        else:
            print(f"\n✅ 所有联赛API访问正常")
            return True


async def check_recent_ingestion_logs():
    """检查最近的摄取日志（通过数据库时间戳）"""
    print("\n" + "=" * 80)
    print("📝 步骤4: 检查数据摄取历史")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        # 查找最近创建的比赛
        stmt = (
            select(Match)
            .order_by(Match.created_at.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        recent_matches = result.scalars().all()
        
        if not recent_matches:
            print("\n❌ 数据库中没有任何比赛记录")
            print("   可能从未运行过数据摄取")
            return False
        
        print(f"\n最近入库的5场比赛:")
        print(f"{'入库时间':<25} {'比赛ID':<30} {'联赛':<10}")
        print("-" * 70)
        
        for match in recent_matches:
            created_time = match.created_at.strftime("%Y-%m-%d %H:%M:%S") if match.created_at else "N/A"
            print(f"{created_time:<25} {match.match_id:<30} {match.league_id:<10}")
        
        # 检查最近更新时间
        stmt = select(func.max(Match.updated_at))
        result = await db.execute(stmt)
        last_update = result.scalar()
        
        if last_update:
            time_since_update = datetime.now(timezone.utc) - last_update
            print(f"\n最后更新时间: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"距今: {time_since_update.total_seconds() / 3600:.1f} 小时")
            
            if time_since_update.total_seconds() > 86400:  # 超过1天
                print("⚠️  数据已经超过1天未更新，建议重新运行摄取")
        
        return True


async def check_entity_resolution():
    """检查实体解析是否正常"""
    print("\n" + "=" * 80)
    print("🔍 步骤5: 检查实体解析器")
    print("=" * 80)
    
    await entity_resolver.initialize()
    
    print(f"\n实体解析器缓存:")
    print(f"   球队缓存: {len(entity_resolver._team_cache)} 条别名")
    print(f"   球队信息: {len(entity_resolver._team_info)} 支球队")
    print(f"   联赛缓存: {len(entity_resolver._league_cache)} 条别名")
    
    if len(entity_resolver._team_cache) == 0:
        print("\n❌ 实体解析器没有加载任何球队数据！")
        print("   这会导致无法匹配球队，数据摄取失败")
        return False
    
    # 测试一些常见球队的解析
    test_teams = [
        ("Manchester United FC", "football-data.org"),
        ("Liverpool FC", "football-data.org"),
        ("FC Bayern München", "football-data.org"),
    ]
    
    print(f"\n测试常见球队名称解析:")
    for team_name, source in test_teams:
        team_id = await entity_resolver.resolve_team(team_name, source)
        if team_id:
            print(f"   ✅ '{team_name}' → {team_id}")
        else:
            print(f"   ⚠️  '{team_name}' → 无法解析")
    
    return True


async def provide_solutions():
    """提供解决方案"""
    print("\n" + "=" * 80)
    print("💡 解决方案建议")
    print("=" * 80)
    
    print("\n根据诊断结果，建议按以下步骤修复：")
    print("\n1️⃣  确保联赛已初始化:")
    print("   python scripts/seed_leagues.py")
    
    print("\n2️⃣  同步球队名称（修复实体解析问题）:")
    print("   python scripts/sync_with_api_names.py")
    
    print("\n3️⃣  重新运行数据摄取:")
    print("   python src/data_pipeline/ingest_football_data_v2.py")
    
    print("\n4️⃣  验证数据:")
    print("   python scripts/inspect_data.py --all")
    
    print("\n如果EPL仍然没有数据，可能的原因:")
    print("   • API计划不支持英超（需要付费）")
    print("   • 联赛代码映射错误（PL vs EPL）")
    print("   • 赛季已结束，没有未来比赛")


async def main():
    """主函数"""
    print("=" * 80)
    print("🔧 数据缺失诊断工具")
    print("=" * 80)
    print("\n正在诊断数据问题...")
    
    try:
        # 执行所有检查
        await check_league_configuration()
        await check_teams_data()
        await check_api_connection()
        await check_recent_ingestion_logs()
        await check_entity_resolution()
        await provide_solutions()
        
        print("\n" + "=" * 80)
        print("✅ 诊断完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

