"""add_product_metadata

Revision ID: 6a9efc626df6
Revises: 636243cbdb6f
Create Date: 2025-11-16 19:13:54.535808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a9efc626df6'
down_revision: Union[str, Sequence[str], None] = '636243cbdb6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 메타데이터 컬럼 추가"""
    # 가격 컬럼 추가
    op.add_column('products', sa.Column('price', sa.Integer(), nullable=True))
    
    # 색상 컬럼 추가
    op.add_column('products', sa.Column('color', sa.String(length=50), nullable=True))
    
    # 카테고리 컬럼 추가
    op.add_column('products', sa.Column('category', sa.String(length=50), nullable=True))
    
    # 시즌 컬럼 추가
    op.add_column('products', sa.Column('season', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema - 메타데이터 컬럼 제거"""
    op.drop_column('products', 'season')
    op.drop_column('products', 'category')
    op.drop_column('products', 'color')
    op.drop_column('products', 'price')