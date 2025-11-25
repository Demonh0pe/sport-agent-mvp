"""add_result_and_updated_at_to_matches

Revision ID: 8bf3467b31d5
Revises: 7a91cbc4a378
Create Date: 2025-11-24 15:51:32.450428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bf3467b31d5'
down_revision: Union[str, Sequence[str], None] = '7a91cbc4a378'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 为 matches 表添加缺失字段和约束。"""
    # 1. 添加 result 列 (H/D/A)
    op.add_column('matches', sa.Column('result', sa.String(length=1), nullable=True))
    
    # 2. 添加 updated_at 列
    op.add_column('matches', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    
    # 3. 添加约束条件
    op.create_check_constraint('check_home_pos', 'matches', 'home_score >= 0')
    op.create_check_constraint('check_away_pos', 'matches', 'away_score >= 0')
    op.create_check_constraint('check_diff_teams', 'matches', 'home_team_id != away_team_id')


def downgrade() -> None:
    """Downgrade schema: 移除添加的字段和约束。"""
    # 移除约束
    op.drop_constraint('check_diff_teams', 'matches', type_='check')
    op.drop_constraint('check_away_pos', 'matches', type_='check')
    op.drop_constraint('check_home_pos', 'matches', type_='check')
    
    # 移除列
    op.drop_column('matches', 'updated_at')
    op.drop_column('matches', 'result')
