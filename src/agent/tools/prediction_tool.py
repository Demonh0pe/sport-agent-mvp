"""
预测工具

为 Agent 提供比赛预测功能
"""
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone

from src.ml.features.match_features import MatchFeatureExtractor
from src.ml.models.match_predictor import MatchPredictor, SimpleRuleBasedPredictor
from src.data_pipeline.entity_resolver import entity_resolver


class PredictionTool:
    """比赛预测工具"""
    
    def __init__(self, model_path: str = "models/match_predictor_baseline.pkl"):
        """
        初始化预测工具
        
        Args:
            model_path: 模型文件路径
        """
        self.feature_extractor = MatchFeatureExtractor()
        self.model_path = model_path
        
        # 尝试加载训练好的模型
        if Path(model_path).exists():
            try:
                self.predictor = MatchPredictor(model_path)
                self.use_ml_model = True
                print(f"成功加载预测模型: {model_path}")
            except Exception as e:
                print(f"加载模型失败: {e}")
                self.predictor = SimpleRuleBasedPredictor()
                self.use_ml_model = False
                print("使用基于规则的预测器")
        else:
            self.predictor = SimpleRuleBasedPredictor()
            self.use_ml_model = False
            print(f"模型文件不存在: {model_path}")
            print("使用基于规则的预测器（准确率较低）")
            print("提示: 运行 'python src/ml/training/train_baseline.py' 训练模型")
    
    async def predict_match(
        self, 
        home_team_name: str,
        away_team_name: str,
        league_name: Optional[str] = None
    ) -> str:
        """
        预测比赛结果
        
        Args:
            home_team_name: 主队名称
            away_team_name: 客队名称
            league_name: 联赛名称（可选）
            
        Returns:
            预测结果的文本描述
        """
        try:
            # 1. 解析球队 ID
            await entity_resolver.initialize()
            
            home_team_id = await entity_resolver.resolve_team(home_team_name)
            away_team_id = await entity_resolver.resolve_team(away_team_name)
            
            if not home_team_id:
                return f"系统提示：未找到球队 '{home_team_name}'"
            if not away_team_id:
                return f"系统提示：未找到球队 '{away_team_name}'"
            
            # 2. 推断联赛 ID（如果未提供）
            if league_name:
                league_id = await entity_resolver.resolve_league(league_name, source="user_query")
                if not league_id:
                    return f"系统提示：未找到联赛 '{league_name}'"
            else:
                # 默认使用主队所在联赛
                from src.infra.db.session import AsyncSessionLocal
                from src.infra.db.models import Team
                from sqlalchemy import select
                
                async with AsyncSessionLocal() as db:
                    stmt = select(Team.league_id).where(Team.team_id == home_team_id)
                    result = await db.execute(stmt)
                    league_id = result.scalar_one_or_none()
                
                if not league_id:
                    return f"系统提示：无法确定联赛信息"
            
            # 3. 提取特征
            features = await self.feature_extractor.extract_features_for_match(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                league_id=league_id,
                match_date=datetime.now(timezone.utc),
                season="2024"
            )
            
            # 4. 预测
            result = self.predictor.predict_single(features)
            
            # 5. 格式化输出
            prediction = result['prediction']
            probs = result['probabilities']
            confidence = result['confidence']
            
            # 预测结果描述
            if prediction == 'H':
                outcome = f"{home_team_name} 主场获胜"
            elif prediction == 'D':
                outcome = "两队战平"
            else:
                outcome = f"{away_team_name} 客场获胜"
            
            # 构造输出
            output = f"""【比赛预测】{home_team_name} vs {away_team_name}

预测结果: {outcome}
置信度: {confidence:.1%}

详细概率:
- {home_team_name} 获胜: {probs['home_win']:.1%}
- 平局: {probs['draw']:.1%}
- {away_team_name} 获胜: {probs['away_win']:.1%}
"""
            
            # 添加预测方法说明
            if not self.use_ml_model:
                output += "\n注: 使用基于规则的预测（训练模型后准确率更高）"
            else:
                output += f"\n注: 基于机器学习模型预测"
            
            # 添加特征分析
            output += f"""

关键因素分析:
- 积分榜排名: {home_team_name} 第{features.get('home_team_rank', 0):.0f}名 vs {away_team_name} 第{features.get('away_team_rank', 0):.0f}名
- 近期状态: {home_team_name} {features.get('home_recent_wins', 0):.0f}胜 vs {away_team_name} {features.get('away_recent_wins', 0):.0f}胜（最近5场）
- 主场优势: {features.get('home_advantage_win_rate', 0):.1%}
"""
            
            return output
            
        except Exception as e:
            return f"预测失败: {str(e)}"


# 全局单例
prediction_tool = PredictionTool()

