#!/usr/bin/env python3
"""
球队中文别名管理工具

功能：
1. 查看数据库架构
2. 查看当前球队数据
3. 批量添加中文别名
4. 语义识别测试

确保后期可扩展：
- 支持批量导入CSV
- 支持手动添加单个别名
- 支持验证别名冲突
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text, inspect
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Team, League
from src.data_pipeline.entity_resolver import entity_resolver


async def show_database_schema():
    """显示数据库架构"""
    print("=" * 80)
    print("数据库架构")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        for table_name in ['leagues', 'teams', 'matches', 'standings']:
            print(f"\n[表: {table_name}]")
            
            # 获取列信息
            stmt = text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            result = await db.execute(stmt)
            columns = result.all()
            
            print(f"  {'列名':<25} {'类型':<20} {'可空':<8} {'默认值':<20}")
            print("  " + "-" * 80)
            for col in columns:
                nullable = "YES" if col.is_nullable == 'YES' else "NO"
                default = str(col.column_default)[:20] if col.column_default else "-"
                print(f"  {col.column_name:<25} {col.data_type:<20} {nullable:<8} {default:<20}")
    
    print("\n" + "=" * 80)


async def show_current_teams():
    """显示当前球队数据（检查中文别名）"""
    print("=" * 80)
    print("当前球队数据分析")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        stmt = select(Team).order_by(Team.league_id, Team.team_name)
        result = await db.execute(stmt)
        teams = result.scalars().all()
        
        has_chinese = 0
        no_chinese = 0
        
        print(f"\n总计: {len(teams)} 支球队\n")
        
        current_league = None
        for team in teams:
            if team.league_id != current_league:
                current_league = team.league_id
                print(f"\n【{current_league}】")
            
            # 检查是否有中文
            has_cn = any('\u4e00' <= c <= '\u9fff' for c in team.team_name)
            marker = "[+]" if has_cn else "[-]"
            
            if has_cn:
                has_chinese += 1
            else:
                no_chinese += 1
            
            print(f"  {marker} {team.team_id:<6} {team.team_name}")
        
        print(f"\n统计:")
        print(f"  有中文别名: {has_chinese} ({has_chinese/len(teams)*100:.1f}%)")
        print(f"  无中文别名: {no_chinese} ({no_chinese/len(teams)*100:.1f}%)")
    
    print("\n" + "=" * 80)


async def add_chinese_aliases_batch():
    """批量添加中文别名"""
    print("=" * 80)
    print("批量添加中文别名")
    print("=" * 80)
    
    # 主要球队的中文别名映射
    chinese_aliases = {
        # 英超
        "MUN": "Manchester United (曼联)",
        "LIV": "Liverpool (利物浦)",
        "ARS": "Arsenal (阿森纳)",
        "MCI": "Manchester City (曼城)",
        "CHE": "Chelsea (切尔西)",
        "TOT": "Tottenham Hotspur (热刺)",
        "NEW": "Newcastle United (纽卡斯尔)",
        "LEI": "Leicester City (莱斯特城)",
        "AVL": "Aston Villa (阿斯顿维拉)",
        "WHU": "West Ham United (西汉姆联)",
        "WOL": "Wolverhampton Wanderers (狼队)",
        "CRY": "Crystal Palace (水晶宫)",
        "BHA": "Brighton & Hove Albion (布莱顿)",
        "EVE": "Everton (埃弗顿)",
        "FUL": "Fulham (富勒姆)",
        "BRE": "Brentford (布伦特福德)",
        "NOT": "Nottingham Forest (诺丁汉森林)",
        "BOU": "AFC Bournemouth (伯恩茅斯)",
        
        # 德甲
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
        
        # 西甲
        "RMA": "Real Madrid (皇家马德里)",
        "FCB": "FC Barcelona (巴塞罗那)",
        "ATM": "Atlético de Madrid (马德里竞技)",
        "SEV": "Sevilla (塞维利亚)",
        "VAL": "Valencia (瓦伦西亚)",
        "VIL": "Villarreal (比利亚雷亚尔)",
        "BET": "Real Betis (皇家贝蒂斯)",
        "RSO": "Real Sociedad (皇家社会)",
        "ATH": "Athletic Club (毕尔巴鄂竞技)",
        "GET": "Getafe (赫塔费)",
        
        # 意甲
        "JUV": "Juventus (尤文图斯)",
        "INT": "Inter Milan (国际米兰)",
        "MIL": "AC Milan (AC米兰)",
        "NAP": "Napoli (那不勒斯)",
        "ROM": "AS Roma (罗马)",
        "LAZ": "Lazio (拉齐奥)",
        "ATA": "Atalanta (亚特兰大)",
        "FIO": "Fiorentina (佛罗伦萨)",
        
        # 法甲
        "PSG": "Paris Saint-Germain (巴黎圣日耳曼)",
        "MAR": "Marseille (马赛)",
        "LYO": "Lyon (里昂)",
        "ASM": "Monaco (摩纳哥)",
        "LIL": "Lille (里尔)",
        "NIC": "Nice (尼斯)",
        "REN": "Rennes (雷恩)",
    }
    
    async with AsyncSessionLocal() as db:
        updated = 0
        skipped = 0
        
        for team_id, new_name in chinese_aliases.items():
            # 查找球队
            stmt = select(Team).where(Team.team_id == team_id)
            result = await db.execute(stmt)
            team = result.scalar_one_or_none()
            
            if team:
                old_name = team.team_name
                
                # 检查是否已有中文
                if '(' in old_name and ')' in old_name:
                    print(f"  [SKIP] {team_id}: 已有别名 - {old_name}")
                    skipped += 1
                else:
                    # 更新名称
                    stmt = text(f"""
                        UPDATE teams 
                        SET team_name = :new_name 
                        WHERE team_id = :team_id
                    """)
                    await db.execute(stmt, {"new_name": new_name, "team_id": team_id})
                    print(f"  [OK] {team_id}: {old_name} -> {new_name}")
                    updated += 1
            else:
                print(f"  [ERROR] {team_id}: 未找到球队")
        
        await db.commit()
        
        print(f"\n结果:")
        print(f"  [OK] 更新: {updated} 个")
        print(f"  [SKIP] 跳过: {skipped} 个")
    
    print("\n" + "=" * 80)


async def test_semantic_recognition():
    """测试语义识别"""
    print("=" * 80)
    print("语义识别测试")
    print("=" * 80)
    
    await entity_resolver.initialize()
    
    test_queries = [
        # 中文
        "曼联", "利物浦", "阿森纳", "曼城", "切尔西",
        "拜仁", "多特", "皇马", "巴萨", "尤文",
        
        # 英文全名
        "Manchester United", "Liverpool", "Bayern München",
        
        # 简称
        "MUN", "LIV", "FCB", "BVB", "RMA",
        
        # 模糊
        "曼", "拜", "皇",
    ]
    
    print("\n测试用例:")
    for query in test_queries:
        team_id = await entity_resolver.resolve_team(query, source="test")
        if team_id:
            team_info = await entity_resolver.get_team_info(team_id)
            print(f"  [OK] '{query:20}' -> {team_id:6} ({team_info['name']})")
        else:
            # 尝试搜索
            results = await entity_resolver.search_teams(query, limit=3)
            if results:
                print(f"  [WARN] '{query:20}' -> 未精确匹配，候选:")
                for r in results:
                    print(f"       - {r['name']} ({r['id']}) [{r['score']:.2%}]")
            else:
                print(f"  [ERROR] '{query:20}' -> 未找到")
    
    print("\n" + "=" * 80)


async def export_teams_to_csv():
    """导出球队数据到CSV（方便编辑）"""
    import csv
    
    print("=" * 80)
    print("导出球队数据到CSV")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        stmt = select(Team).order_by(Team.league_id, Team.team_id)
        result = await db.execute(stmt)
        teams = result.scalars().all()
        
        csv_file = "data/teams_aliases.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['team_id', 'current_name', 'suggested_name_with_chinese'])
            
            for team in teams:
                # 如果已有中文，保持原样
                if '(' in team.team_name and ')' in team.team_name:
                    suggested = team.team_name
                else:
                    # 建议添加中文（需要手动填写）
                    suggested = f"{team.team_name} (TODO: 添加中文)"
                
                writer.writerow([team.team_id, team.team_name, suggested])
        
        print(f"\n[OK] 导出完成: {csv_file}")
        print(f"   总计: {len(teams)} 支球队")
        print(f"\n使用方法:")
        print(f"  1. 在Excel中打开 {csv_file}")
        print(f"  2. 编辑 'suggested_name_with_chinese' 列")
        print(f"  3. 保存文件")
        print(f"  4. 运行导入命令")
    
    print("\n" + "=" * 80)


async def import_teams_from_csv():
    """从CSV导入球队别名"""
    import csv
    
    print("=" * 80)
    print("从CSV导入球队别名")
    print("=" * 80)
    
    csv_file = "data/teams_aliases.csv"
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            aliases = list(reader)
        
        async with AsyncSessionLocal() as db:
            updated = 0
            
            for row in aliases:
                team_id = row['team_id']
                new_name = row['suggested_name_with_chinese']
                
                # 跳过TODO项
                if 'TODO' in new_name:
                    continue
                
                stmt = text("""
                    UPDATE teams 
                    SET team_name = :new_name 
                    WHERE team_id = :team_id
                """)
                await db.execute(stmt, {"new_name": new_name, "team_id": team_id})
                print(f"  [OK] {team_id}: -> {new_name}")
                updated += 1
            
            await db.commit()
            print(f"\n[OK] 导入完成: {updated} 个球队")
    
    except FileNotFoundError:
        print(f"[ERROR] 文件不存在: {csv_file}")
        print(f"   请先运行导出命令")
    
    print("\n" + "=" * 80)


async def main():
    """主菜单"""
    while True:
        print("\n" + "=" * 80)
        print("球队中文别名管理工具")
        print("=" * 80)
        print("\n选择操作:")
        print("  1. 查看数据库架构")
        print("  2. 查看当前球队数据")
        print("  3. 批量添加主要球队中文别名")
        print("  4. 测试语义识别")
        print("  5. 导出球队数据到CSV（方便手动编辑）")
        print("  6. 从CSV导入球队别名")
        print("  0. 退出")
        
        choice = input("\n请输入选项 (0-6): ").strip()
        
        if choice == "1":
            await show_database_schema()
        elif choice == "2":
            await show_current_teams()
        elif choice == "3":
            confirm = input("\n确认批量添加中文别名? (y/n): ").strip().lower()
            if confirm == 'y':
                await add_chinese_aliases_batch()
                print("\n[OK] 完成！EntityResolver将在下次初始化时自动加载新别名")
        elif choice == "4":
            await test_semantic_recognition()
        elif choice == "5":
            await export_teams_to_csv()
        elif choice == "6":
            confirm = input("\n确认从CSV导入? (y/n): ").strip().lower()
            if confirm == 'y':
                await import_teams_from_csv()
        elif choice == "0":
            print("\n再见!")
            break
        else:
            print("\n[ERROR] 无效选项，请重试")


if __name__ == "__main__":
    import os
    
    # 创建data目录
    os.makedirs("data", exist_ok=True)
    
    # 运行主程序
    asyncio.run(main())

