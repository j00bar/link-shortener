"""Added click count

Revision ID: a8890016b39c
Revises: 127a58bfa903
Create Date: 2022-12-04 15:43:33.590837

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a8890016b39c"
down_revision = "127a58bfa903"
branch_labels = ()
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("shortened_link", sa.Column("clicks", sa.Integer(), default=0))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("shortened_link", "clicks")
    # ### end Alembic commands ###