"""
获取完整赛季数据的脚本

用法: python scripts/ingest_full_season.py
"""
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from src.data_pipeline.ingest_football_data_v2 import FootballDataIngester


async def main():
    """获取完整赛季数据（回溯180天）"""
    print("=" * 80)
    print("[任务] 完整赛季数据摄取")
    print("=" * 80)
    print("\n[等待] 这可能需要几分钟时间，请耐心等待...\n")
    
    ingester = FootballDataIngester()
    
    # 摄取完整赛季数据（回溯180天，覆盖大部分赛季）
    await ingester.run_full_ingestion(
        leagues=["PL", "BL1", "PD", "SA", "FL1", "CL"],
        days_back=180  # 回溯180天（约6个月）
    )
    
    print("\n[完成] 现在您应该有更完整的赛季数据了。")
    print("[提示] 运行以下命令验证: python scripts/inspect_data.py --expected")


if __name__ == "__main__":
    asyncio.run(main())

