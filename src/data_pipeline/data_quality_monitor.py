"""
数据质量监控服务

监控指标：
1. 数据新鲜度：最后更新时间
2. 数据完整性：必填字段缺失率
3. 数据一致性：比分与结果是否匹配
4. 数据异常：异常比分、异常时间
5. 覆盖率：各联赛数据覆盖情况
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from collections import defaultdict
import logging

sys.path.append(os.getcwd())

from sqlalchemy import select, func, and_, or_
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Match, Team, League, News

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self):
        self.report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {},
            "alerts": [],
            "summary": {}
        }
    
    async def check_data_freshness(self):
        """检查数据新鲜度"""
        async with AsyncSessionLocal() as db:
            # 最近更新时间
            stmt = select(func.max(Match.updated_at))
            result = await db.execute(stmt)
            last_update = result.scalar()
            
            if last_update:
                age_hours = (datetime.now(timezone.utc) - last_update.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                self.report["metrics"]["last_update_hours_ago"] = round(age_hours, 2)
                
                if age_hours > 24:
                    self.report["alerts"].append({
                        "severity": "warning",
                        "message": f"数据已超过 {age_hours:.1f} 小时未更新"
                    })
            else:
                self.report["alerts"].append({
                    "severity": "error",
                    "message": "数据库中无任何比赛数据"
                })
    
    async def check_data_completeness(self):
        """检查数据完整性"""
        async with AsyncSessionLocal() as db:
            # 总比赛数
            stmt = select(func.count(Match.match_id))
            result = await db.execute(stmt)
            total_matches = result.scalar()
            
            # 已完成比赛中缺少比分的数量
            stmt = select(func.count(Match.match_id)).where(
                and_(
                    Match.status == "FINISHED",
                    or_(Match.home_score.is_(None), Match.away_score.is_(None))
                )
            )
            result = await db.execute(stmt)
            missing_scores = result.scalar()
            
            # 缺少结果字段的已完成比赛
            stmt = select(func.count(Match.match_id)).where(
                and_(
                    Match.status == "FINISHED",
                    Match.result.is_(None)
                )
            )
            result = await db.execute(stmt)
            missing_results = result.scalar()
            
            self.report["metrics"]["total_matches"] = total_matches
            self.report["metrics"]["missing_scores"] = missing_scores
            self.report["metrics"]["missing_results"] = missing_results
            
            if missing_scores > 0:
                self.report["alerts"].append({
                    "severity": "warning",
                    "message": f"{missing_scores} 场已完成比赛缺少比分数据"
                })
            
            if missing_results > 0:
                self.report["alerts"].append({
                    "severity": "warning",
                    "message": f"{missing_results} 场已完成比赛缺少结果字段"
                })
    
    async def check_data_consistency(self):
        """检查数据一致性"""
        async with AsyncSessionLocal() as db:
            # 比分与结果不匹配的记录
            stmt = select(Match).where(
                and_(
                    Match.status == "FINISHED",
                    Match.home_score.isnot(None),
                    Match.away_score.isnot(None),
                    Match.result.isnot(None)
                )
            )
            result = await db.execute(stmt)
            matches = result.scalars().all()
            
            inconsistent_count = 0
            for match in matches:
                expected_result = None
                if match.home_score > match.away_score:
                    expected_result = "H"
                elif match.home_score < match.away_score:
                    expected_result = "A"
                else:
                    expected_result = "D"
                
                if match.result != expected_result:
                    inconsistent_count += 1
                    logger.warning(
                        f"数据不一致: {match.match_id} - "
                        f"比分 {match.home_score}:{match.away_score} "
                        f"但结果为 {match.result} (预期: {expected_result})"
                    )
            
            self.report["metrics"]["inconsistent_results"] = inconsistent_count
            
            if inconsistent_count > 0:
                self.report["alerts"].append({
                    "severity": "error",
                    "message": f"{inconsistent_count} 场比赛的比分与结果字段不一致"
                })
    
    async def check_data_anomalies(self):
        """检查数据异常"""
        async with AsyncSessionLocal() as db:
            # 异常高分 (>10球)
            stmt = select(Match).where(
                or_(Match.home_score > 10, Match.away_score > 10)
            )
            result = await db.execute(stmt)
            high_score_matches = result.scalars().all()
            
            # 未来时间的已完成比赛
            stmt = select(Match).where(
                and_(
                    Match.status == "FINISHED",
                    Match.match_date > datetime.now(timezone.utc)
                )
            )
            result = await db.execute(stmt)
            future_finished = result.scalars().all()
            
            self.report["metrics"]["anomaly_high_scores"] = len(high_score_matches)
            self.report["metrics"]["anomaly_future_finished"] = len(future_finished)
            
            if high_score_matches:
                self.report["alerts"].append({
                    "severity": "warning",
                    "message": f"{len(high_score_matches)} 场比赛出现异常高分（>10球），请人工审核"
                })
            
            if future_finished:
                self.report["alerts"].append({
                    "severity": "error",
                    "message": f"{len(future_finished)} 场比赛标记为已完成但比赛时间在未来"
                })
    
    async def check_league_coverage(self):
        """检查各联赛数据覆盖情况"""
        async with AsyncSessionLocal() as db:
            # 按联赛统计比赛数量
            stmt = select(
                Match.league_id,
                func.count(Match.match_id).label('match_count'),
                func.count(Match.match_id).filter(Match.status == 'FINISHED').label('finished_count')
            ).group_by(Match.league_id)
            
            result = await db.execute(stmt)
            league_stats = result.all()
            
            coverage = {}
            for league_id, total, finished in league_stats:
                coverage[league_id] = {
                    "total_matches": total,
                    "finished_matches": finished,
                    "completion_rate": round(finished / total * 100, 2) if total > 0 else 0
                }
            
            self.report["metrics"]["league_coverage"] = coverage
            
            # 检查是否有联赛数据过少
            for league_id, stats in coverage.items():
                if stats["total_matches"] < 10:
                    self.report["alerts"].append({
                        "severity": "info",
                        "message": f"联赛 {league_id} 仅有 {stats['total_matches']} 场比赛数据"
                    })
    
    async def check_upcoming_matches(self):
        """检查未来比赛数据"""
        async with AsyncSessionLocal() as db:
            # 未来7天的比赛数量
            now = datetime.now(timezone.utc)
            future_7d = now + timedelta(days=7)
            
            stmt = select(func.count(Match.match_id)).where(
                and_(
                    Match.match_date >= now,
                    Match.match_date <= future_7d,
                    Match.status == "FIXTURE"
                )
            )
            result = await db.execute(stmt)
            upcoming_count = result.scalar()
            
            self.report["metrics"]["upcoming_matches_7d"] = upcoming_count
            
            if upcoming_count == 0:
                self.report["alerts"].append({
                    "severity": "warning",
                    "message": "未来7天无预告比赛数据"
                })
    
    async def generate_summary(self):
        """生成摘要"""
        alert_counts = defaultdict(int)
        for alert in self.report["alerts"]:
            alert_counts[alert["severity"]] += 1
        
        self.report["summary"] = {
            "total_alerts": len(self.report["alerts"]),
            "alert_breakdown": dict(alert_counts),
            "health_status": "healthy" if alert_counts.get("error", 0) == 0 else "unhealthy"
        }
    
    async def run_full_check(self) -> Dict:
        """运行完整的数据质量检查"""
        logger.info("开始数据质量检查...")
        
        await self.check_data_freshness()
        await self.check_data_completeness()
        await self.check_data_consistency()
        await self.check_data_anomalies()
        await self.check_league_coverage()
        await self.check_upcoming_matches()
        await self.generate_summary()
        
        logger.info("数据质量检查完成！")
        return self.report
    
    def print_report(self):
        """打印报告"""
        print("\n" + "="*60)
        print("[统计] 数据质量监控报告")
        print("="*60)
        print(f"[时间] 检查时间: {self.report['timestamp']}")
        print(f"[健康] 健康状态: {self.report['summary']['health_status'].upper()}")
        print(f"[警告] 告警数量: {self.report['summary']['total_alerts']}")
        print()
        
        # 关键指标
        print("[数据] 关键指标:")
        metrics = self.report['metrics']
        print(f"  - 总比赛数: {metrics.get('total_matches', 0)}")
        print(f"  - 最后更新: {metrics.get('last_update_hours_ago', 'N/A')} 小时前")
        print(f"  - 未来7天比赛: {metrics.get('upcoming_matches_7d', 0)} 场")
        print()
        
        # 告警信息
        if self.report['alerts']:
            print("[告警] 告警详情:")
            for i, alert in enumerate(self.report['alerts'], 1):
                severity_text = {
                    "error": "[错误]",
                    "warning": "[警告]",
                    "info": "[信息]"
                }
                text = severity_text.get(alert['severity'], '[标记]')
                print(f"  {i}. {text} [{alert['severity'].upper()}] {alert['message']}")
        else:
            print("[OK] 无告警信息，数据质量良好！")
        
        print("="*60 + "\n")


async def main():
    """主函数"""
    monitor = DataQualityMonitor()
    await monitor.run_full_check()
    monitor.print_report()
    
    # 可选：保存报告到文件
    import json
    with open("data_quality_report.json", "w", encoding="utf-8") as f:
        json.dump(monitor.report, f, indent=2, ensure_ascii=False)
    print("[文件] 详细报告已保存到: data_quality_report.json")


if __name__ == "__main__":
    asyncio.run(main())

