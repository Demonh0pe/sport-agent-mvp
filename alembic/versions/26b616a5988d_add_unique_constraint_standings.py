"""add_unique_constraint_standings

Revision ID: 26b616a5988d
Revises: ece2ff06a99b
Create Date: 2025-11-27 15:31:57.023843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26b616a5988d'
down_revision: Union[str, Sequence[str], None] = 'ece2ff06a99b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
