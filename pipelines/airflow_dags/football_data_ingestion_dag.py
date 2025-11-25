"""
Airflow DAG: Football Data 摄取管道

调度策略：
- 每天 03:00 UTC 全量更新（赛后数据同步）
- 每小时增量更新（赛中数据同步）
- 比赛日前后加密集监控

依赖：
- PostgreSQL (数据库)
- Football-data.org API
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
import os

# 确保可以导入项目代码
sys.path.append('/app')  # Docker 容器中的项目路径，本地开发时需要调整

# 默认参数
default_args = {
    'owner': 'sport-agent-team',
    'depends_on_past': False,
    'email': ['alerts@sport-agent.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}


def run_data_ingestion(**context):
    """运行数据摄取任务"""
    import asyncio
    from src.data_pipeline.ingest_football_data_v2 import FootballDataIngester
    
    ingester = FootballDataIngester()
    
    # 根据任务类型选择策略
    task_type = context.get('params', {}).get('task_type', 'incremental')
    
    if task_type == 'full':
        # 全量更新：所有联赛
        leagues = ["PL", "BL1", "PD", "SA", "FL1", "CL"]
        asyncio.run(ingester.run_full_ingestion(leagues=leagues))
    else:
        # 增量更新：仅主要联赛
        leagues = ["PL", "BL1"]  # 根据实际需求调整
        asyncio.run(ingester.run_full_ingestion(leagues=leagues))
    
    # 返回统计信息
    return ingester.stats


def validate_data_quality(**context):
    """数据质量检查"""
    import asyncio
    from sqlalchemy import select, func
    from src.infra.db.session import AsyncSessionLocal
    from src.infra.db.models import Match
    
    async def check_quality():
        async with AsyncSessionLocal() as db:
            # 检查1: 今天是否有新数据
            today_start = datetime.now().replace(hour=0, minute=0, second=0)
            stmt = select(func.count(Match.match_id)).where(
                Match.created_at >= today_start
            )
            result = await db.execute(stmt)
            today_count = result.scalar()
            
            if today_count == 0:
                raise ValueError("数据质量告警: 今日无新增比赛数据！")
            
            # 检查2: 是否有异常比分
            stmt = select(Match).where(
                Match.status == "FINISHED",
                Match.home_score > 15  # 异常高分
            )
            result = await db.execute(stmt)
            anomalies = result.scalars().all()
            
            if anomalies:
                print(f"发现 {len(anomalies)} 场异常比分，需要人工审核")
            
            print(f"数据质量检查通过: 今日新增 {today_count} 场比赛")
            return {"today_count": today_count, "anomalies": len(anomalies)}
    
    return asyncio.run(check_quality())


def send_summary_notification(**context):
    """发送摘要通知（可集成 Slack/钉钉/邮件）"""
    task_instance = context['task_instance']
    stats = task_instance.xcom_pull(task_ids='ingest_data')
    quality = task_instance.xcom_pull(task_ids='validate_quality')
    
    message = f"""
    📊 Football Data 摄取任务完成
    
    ✅ 成功入库: {stats.get('successfully_ingested', 0)} 场
    ⚠️  实体解析失败: {stats.get('failed_resolution', 0)} 场
    ❌ 错误: {stats.get('errors', 0)} 场
    
    📈 数据质量:
    - 今日新增: {quality.get('today_count', 0)} 场
    - 异常记录: {quality.get('anomalies', 0)} 场
    
    执行时间: {context['execution_date']}
    """
    
    print(message)
    # TODO: 集成实际通知渠道
    # slack_webhook(message)
    # dingtalk_webhook(message)


# ========================
# DAG 1: 每日全量更新
# ========================
with DAG(
    'football_data_daily_full_sync',
    default_args=default_args,
    description='每日全量同步 Football Data',
    schedule_interval='0 3 * * *',  # 每天 03:00 UTC
    start_date=days_ago(1),
    catchup=False,
    tags=['data-ingestion', 'football-data', 'daily'],
) as dag_daily:
    
    task_ingest = PythonOperator(
        task_id='ingest_data',
        python_callable=run_data_ingestion,
        params={'task_type': 'full'},
        provide_context=True,
    )
    
    task_validate = PythonOperator(
        task_id='validate_quality',
        python_callable=validate_data_quality,
        provide_context=True,
    )
    
    task_notify = PythonOperator(
        task_id='send_notification',
        python_callable=send_summary_notification,
        provide_context=True,
    )
    
    # 任务依赖
    task_ingest >> task_validate >> task_notify


# ========================
# DAG 2: 每小时增量更新
# ========================
with DAG(
    'football_data_hourly_incremental',
    default_args=default_args,
    description='每小时增量同步 Football Data（赛中更新）',
    schedule_interval='0 * * * *',  # 每小时
    start_date=days_ago(1),
    catchup=False,
    tags=['data-ingestion', 'football-data', 'hourly'],
) as dag_hourly:
    
    task_ingest_incremental = PythonOperator(
        task_id='ingest_data_incremental',
        python_callable=run_data_ingestion,
        params={'task_type': 'incremental'},
        provide_context=True,
    )
    
    task_validate_incremental = PythonOperator(
        task_id='validate_quality',
        python_callable=validate_data_quality,
        provide_context=True,
    )
    
    # 任务依赖
    task_ingest_incremental >> task_validate_incremental


# ========================
# DAG 3: 按需手动触发
# ========================
with DAG(
    'football_data_manual_trigger',
    default_args=default_args,
    description='手动触发的数据摄取任务',
    schedule_interval=None,  # 无自动调度
    start_date=days_ago(1),
    catchup=False,
    tags=['data-ingestion', 'football-data', 'manual'],
) as dag_manual:
    
    task_manual = PythonOperator(
        task_id='manual_ingest',
        python_callable=run_data_ingestion,
        params={'task_type': 'full'},
        provide_context=True,
    )

