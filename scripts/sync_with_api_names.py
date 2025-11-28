#!/usr/bin/env python3
"""
同步数据库球队名称与 Football-data.org API 的官方名称

策略：
1. 保留中文别名（用户体验）
2. 添加 API 完整官方名称（精确匹配）
3. 格式："{API官方名称} ({中文名})"

这样可以确保：
- EntityResolver 精确匹配 成功
- 用户查询中文名 成功
- Agent 显示中文名 成功
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.infra.db.session import AsyncSessionLocal


# Football-data.org API 实际返回的球队名称映射
# 格式: team_id -> "API官方名称 (中文名)"
API_OFFICIAL_NAMES = {
    # ===== 英超 (PL) =====
    "MUN": "Manchester United FC (曼联)",
    "LIV": "Liverpool FC (利物浦)",
    "ARS": "Arsenal FC (阿森纳)",
    "MCI": "Manchester City FC (曼城)",
    "CHE": "Chelsea FC (切尔西)",
    "TOT": "Tottenham Hotspur FC (热刺)",
    "NEW": "Newcastle United FC (纽卡斯尔)",
    "AVL": "Aston Villa FC (阿斯顿维拉)",
    "WHU": "West Ham United FC (西汉姆联)",
    "WOL": "Wolverhampton Wanderers FC (狼队)",
    "CRY": "Crystal Palace FC (水晶宫)",
    "BHA": "Brighton & Hove Albion FC (布莱顿)",
    "EVE": "Everton FC (埃弗顿)",
    "FUL": "Fulham FC (富勒姆)",
    "BRE": "Brentford FC (布伦特福德)",
    "NOT": "Nottingham Forest FC (诺丁汉森林)",
    "BOU": "AFC Bournemouth (伯恩茅斯)",
    "SOU": "Southampton FC (南安普顿)",
    "BUR": "Burnley FC (伯恩利)",
    "LUT": "Luton Town FC (卢顿)",
    "SHU": "Sheffield United FC (谢菲尔德联)",
    
    # ===== 德甲 (BL1) =====
    "FCB": "FC Bayern München (拜仁慕尼黑)",
    "BVB": "Borussia Dortmund (多特蒙德)",
    "RBL": "RB Leipzig (莱比锡红牛)",
    "B04": "Bayer 04 Leverkusen (勒沃库森)",
    "SGE": "Eintracht Frankfurt (法兰克福)",
    "WOB": "VfL Wolfsburg (沃尔夫斯堡)",
    "BMG": "Borussia Mönchengladbach (门兴格拉德巴赫)",
    "SCF": "SC Freiburg (弗赖堡)",
    "M05": "1. FSV Mainz 05 (美因茨)",
    "SVW": "SV Werder Bremen (不来梅)",
    "VFB": "VfB Stuttgart (斯图加特)",
    "FCA": "FC Augsburg (奥格斯堡)",
    "UNB": "1. FC Union Berlin (柏林联合)",
    "TSG": "TSG 1899 Hoffenheim (霍芬海姆)",
    "BOC": "VfL Bochum 1848 (波鸿)",
    "KOE": "1. FC Köln (科隆)",
    
    # ===== 西甲 (PD) =====
    "RMA": "Real Madrid CF (皇家马德里)",
    "BAR": "FC Barcelona (巴塞罗那)",
    "ATM": "Club Atlético de Madrid (马德里竞技)",
    "SEV": "Sevilla FC (塞维利亚)",
    "VAL": "Valencia CF (瓦伦西亚)",
    "VIL": "Villarreal CF (比利亚雷亚尔)",
    "BET": "Real Betis Balompié (皇家贝蒂斯)",
    "RSO": "Real Sociedad de Fútbol (皇家社会)",
    "ATH": "Athletic Club (毕尔巴鄂竞技)",
    "GET": "Getafe CF (赫塔费)",
    "CEL": "RC Celta de Vigo (维戈塞尔塔)",
    "GIR": "Girona FC (赫罗纳)",
    "OSA": "CA Osasuna (奥萨苏纳)",
    "GRA": "Granada CF (格拉纳达)",
    
    # ===== 意甲 (SA) =====
    "JUV": "Juventus FC (尤文图斯)",
    "INT": "FC Internazionale Milano (国际米兰)",
    "MIL": "AC Milan (AC米兰)",
    "NAP": "SSC Napoli (那不勒斯)",
    "ROM": "AS Roma (罗马)",
    "LAZ": "SS Lazio (拉齐奥)",
    "ATA": "Atalanta BC (亚特兰大)",
    "FIO": "ACF Fiorentina (佛罗伦萨)",
    "TOR": "Torino FC (都灵)",
    "BOL": "Bologna FC 1909 (博洛尼亚)",
    "UDI": "Udinese Calcio (乌迪内斯)",
    "SAS": "US Sassuolo Calcio (萨索洛)",
    "VER": "Hellas Verona FC (维罗纳)",
    "MON": "AC Monza (蒙扎)",
    
    # ===== 法甲 (FL1) =====
    "PSG": "Paris Saint-Germain FC (巴黎圣日耳曼)",
    "MAR": "Olympique de Marseille (马赛)",
    "LYO": "Olympique Lyonnais (里昂)",
    "ASM": "AS Monaco FC (摩纳哥)",
    "LIL": "Lille OSC (里尔)",
    "NIC": "OGC Nice (尼斯)",
    "REN": "Stade Rennais FC 1901 (雷恩)",
    "LEN": "RC Lens (朗斯)",
    "STR": "RC Strasbourg Alsace (斯特拉斯堡)",
    "MON": "Montpellier HSC (蒙彼利埃)",
    "NAN": "FC Nantes (南特)",
    "ANG": "Angers SCO (昂热)",
    "REI": "Stade de Reims (兰斯)",
    "TOU": "Toulouse FC (图卢兹)",
    "CLE": "Clermont Foot 63 (克莱蒙)",
    "AJA": "AJ Auxerre (欧塞尔)",
    
    # ===== 欧冠 (CL) =====
    "BEN": "Sport Lisboa e Benfica (本菲卡)",
    "POR": "FC Porto (波尔图)",
    "SCP": "Sporting Clube de Portugal (里斯本竞技)",
    "PSV": "PSV (埃因霍温)",
}

# 特殊处理：同一 team_id 在不同联赛
LEAGUE_SPECIFIC_NAMES = {
    "BRE": {
        "PL": "Brentford FC (布伦特福德)",
        "FL1": "Stade Brestois 29 (布雷斯特)",
    },
    "AJA": {
        "CL": "AFC Ajax (阿贾克斯)",
        "FL1": "AJ Auxerre (欧塞尔)",
    },
    "FCB": {
        "BL1": "FC Bayern München (拜仁慕尼黑)",
        "PD": "FC Barcelona (巴塞罗那)",
    },
}


async def sync_api_names():
    """同步 API 官方名称到数据库"""
    print("=" * 80)
    print("[同步] 同步 API 官方名称到数据库")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        updated = 0
        
        # 1. 处理通用球队
        for team_id, api_name in API_OFFICIAL_NAMES.items():
            stmt = text("""
                UPDATE teams 
                SET team_name = :new_name 
                WHERE team_id = :team_id
            """)
            result = await db.execute(stmt, {"new_name": api_name, "team_id": team_id})
            if result.rowcount > 0:
                print(f"  [更新] {team_id:6} -> {api_name}")
                updated += result.rowcount
        
        # 2. 处理冲突球队（按联赛）
        print("\n处理冲突球队（同一 ID 不同联赛）:")
        for team_id, league_map in LEAGUE_SPECIFIC_NAMES.items():
            for league_id, api_name in league_map.items():
                stmt = text("""
                    UPDATE teams 
                    SET team_name = :new_name 
                    WHERE team_id = :team_id AND league_id = :league_id
                """)
                result = await db.execute(stmt, {
                    "new_name": api_name,
                    "team_id": team_id,
                    "league_id": league_id
                })
                if result.rowcount > 0:
                    print(f"  [更新] {team_id:6} @ {league_id:6} -> {api_name}")
                    updated += result.rowcount
        
        await db.commit()
        
        print(f"\n完成！共更新 {updated} 个球队")
    
    print("\n" + "=" * 80)


async def verify_sync():
    """验证同步效果"""
    print("=" * 80)
    print("[验证] 验证同步效果")
    print("=" * 80)
    
    from src.data_pipeline.entity_resolver import entity_resolver
    
    # 重新初始化 EntityResolver
    entity_resolver._initialized = False
    await entity_resolver.initialize()
    
    # 测试 API 实际返回的名称
    test_cases = [
        # 之前失败的
        "Real Sociedad de Fútbol",
        "RC Celta de Vigo",
        "Real Betis Balompié",
        "FC Barcelona",
        "US Sassuolo Calcio",
        "Bologna FC 1909",
        "Atalanta BC",
        "SSC Napoli",
        "ACF Fiorentina",
        "FC Internazionale Milano",
        "Udinese Calcio",
        "SS Lazio",
        "Stade Brestois 29",
        "Lille OSC",
        "FC Nantes",
        "Angers SCO",
        "Stade Rennais FC 1901",
        "OGC Nice",
        "AS Monaco FC",
        "Olympique Lyonnais",
        "Olympique de Marseille",
        "Sport Lisboa e Benfica",
        "AFC Ajax",
        # 常见的
        "Manchester United FC",
        "FC Bayern München",
        "Paris Saint-Germain FC",
    ]
    
    print("\n测试 API 球队名称解析:")
    success = 0
    failed = 0
    
    for external_name in test_cases:
        team_id = await entity_resolver.resolve_team(
            external_name,
            source="football-data.org",
            fuzzy_threshold=0.85
        )
        
        if team_id:
            team_info = await entity_resolver.get_team_info(team_id)
            print(f"  [OK] {external_name:40} -> {team_id:6}")
            success += 1
        else:
            print(f"  [失败] {external_name:40} -> 无法解析")
            failed += 1
    
    print(f"\n测试结果: {success} 成功 / {failed} 失败 ({success/(success+failed)*100:.1f}%)")
    
    print("\n" + "=" * 80)


async def main():
    """主函数"""
    print("\n[同步] API 名称同步工具\n")
    
    # 步骤 1: 同步名称
    await sync_api_names()
    
    # 步骤 2: 验证效果
    await verify_sync()
    
    print("\n" + "=" * 80)
    print("[完成] 同步完成！")
    print("=" * 80)
    print("\n下一步:")
    print("  运行数据摄取脚本验证:")
    print("  python src/data_pipeline/ingest_football_data_v2.py")
    print("\n  应该不再出现警告！")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

