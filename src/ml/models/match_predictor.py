"""
比赛预测模型

使用 XGBoost 进行比赛结果预测（胜/平/负）
"""
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
from datetime import datetime

try:
    import xgboost as xgb
    from sklearn.preprocessing import LabelEncoder
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("警告: XGBoost 未安装，预测功能不可用")


class MatchPredictor:
    """比赛结果预测器"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化预测器
        
        Args:
            model_path: 模型文件路径
        """
        self.model = None
        self.label_encoder = None
        self.feature_names = None
        self.is_trained = False
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
    
    def train(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        params: Optional[Dict] = None
    ):
        """
        训练模型
        
        Args:
            X_train: 训练特征
            y_train: 训练标签 (H/D/A)
            X_val: 验证特征
            y_val: 验证标签
            params: XGBoost 参数
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost 未安装，请运行: pip install xgboost")
        
        # 编码标签: H -> 0, D -> 1, A -> 2
        self.label_encoder = LabelEncoder()
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        
        # 默认参数
        if params is None:
            params = {
                'objective': 'multi:softprob',
                'num_class': 3,
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'eval_metric': 'mlogloss'
            }
        
        # 训练模型
        self.model = xgb.XGBClassifier(**params)
        
        if X_val is not None and y_val is not None:
            y_val_encoded = self.label_encoder.transform(y_val)
            eval_set = [(X_train, y_train_encoded), (X_val, y_val_encoded)]
            self.model.fit(
                X_train, 
                y_train_encoded,
                eval_set=eval_set,
                verbose=False
            )
        else:
            self.model.fit(X_train, y_train_encoded)
        
        self.is_trained = True
        print("模型训练完成")
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测比赛结果
        
        Args:
            X: 特征数组
            
        Returns:
            (predictions, probabilities)
            predictions: 预测类别 (H/D/A)
            probabilities: 预测概率 [[P(H), P(D), P(A)], ...]
        """
        if not self.is_trained or self.model is None:
            raise ValueError("模型尚未训练或加载")
        
        # 预测概率
        probabilities = self.model.predict_proba(X)
        
        # 预测类别
        predictions_encoded = self.model.predict(X)
        predictions = self.label_encoder.inverse_transform(predictions_encoded)
        
        return predictions, probabilities
    
    def predict_single(self, features: Dict[str, float]) -> Dict[str, any]:
        """
        预测单场比赛
        
        Args:
            features: 特征字典
            
        Returns:
            预测结果字典，包含预测类别和概率
        """
        if not self.is_trained or self.model is None:
            raise ValueError("模型尚未训练或加载")
        
        # 将特征字典转换为数组
        if self.feature_names is None:
            raise ValueError("特征名称未定义")
        
        X = np.array([[features.get(name, 0.0) for name in self.feature_names]])
        
        # 预测
        predictions, probabilities = self.predict(X)
        
        result = {
            "prediction": predictions[0],
            "probabilities": {
                "home_win": float(probabilities[0][self.label_encoder.transform(['H'])[0]]),
                "draw": float(probabilities[0][self.label_encoder.transform(['D'])[0]]),
                "away_win": float(probabilities[0][self.label_encoder.transform(['A'])[0]])
            },
            "confidence": float(max(probabilities[0]))
        }
        
        return result
    
    def save_model(self, path: str):
        """保存模型到文件"""
        if not self.is_trained or self.model is None:
            raise ValueError("模型尚未训练")
        
        model_data = {
            'model': self.model,
            'label_encoder': self.label_encoder,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"模型已保存到: {path}")
    
    def load_model(self, path: str):
        """从文件加载模型"""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.label_encoder = model_data['label_encoder']
        self.feature_names = model_data.get('feature_names')
        self.is_trained = model_data.get('is_trained', True)
        
        print(f"模型已从 {path} 加载")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if not self.is_trained or self.model is None:
            raise ValueError("模型尚未训练")
        
        if self.feature_names is None:
            raise ValueError("特征名称未定义")
        
        importances = self.model.feature_importances_
        return dict(zip(self.feature_names, importances))


class SimpleRuleBasedPredictor:
    """
    简单的基于规则的预测器（作为 Baseline）
    
    当 XGBoost 不可用或模型未训练时使用
    """
    
    def predict_single(self, features: Dict[str, float]) -> Dict[str, any]:
        """
        基于简单规则预测比赛结果
        
        规则：
        1. 排名差距大于10 -> 排名高的球队胜率70%
        2. 近期状态好（3胜以上） -> 胜率提升
        3. 主场优势 -> 主队胜率提升10%
        """
        home_rank = features.get("home_team_rank", 10)
        away_rank = features.get("away_team_rank", 10)
        home_recent_wins = features.get("home_recent_wins", 0)
        away_recent_wins = features.get("away_recent_wins", 0)
        home_advantage = features.get("home_advantage_win_rate", 0.5)
        
        # 基础概率
        home_prob = 0.4
        draw_prob = 0.3
        away_prob = 0.3
        
        # 排名因素
        rank_diff = away_rank - home_rank
        if rank_diff > 5:
            home_prob += 0.2
            away_prob -= 0.15
        elif rank_diff < -5:
            away_prob += 0.2
            home_prob -= 0.15
        
        # 近期状态
        if home_recent_wins >= 3:
            home_prob += 0.1
            draw_prob -= 0.05
        if away_recent_wins >= 3:
            away_prob += 0.1
            draw_prob -= 0.05
        
        # 主场优势
        home_prob += (home_advantage - 0.5) * 0.2
        
        # 归一化
        total = home_prob + draw_prob + away_prob
        home_prob /= total
        draw_prob /= total
        away_prob /= total
        
        # 确定预测结果
        probs = [home_prob, draw_prob, away_prob]
        labels = ['H', 'D', 'A']
        prediction = labels[np.argmax(probs)]
        
        return {
            "prediction": prediction,
            "probabilities": {
                "home_win": float(home_prob),
                "draw": float(draw_prob),
                "away_win": float(away_prob)
            },
            "confidence": float(max(probs)),
            "method": "rule_based"
        }

