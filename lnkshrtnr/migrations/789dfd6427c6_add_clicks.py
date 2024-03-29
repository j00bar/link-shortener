"""add clicks

Revision ID: 789dfd6427c6
Revises: a8890016b39c
Create Date: 2023-06-15 23:45:14.749045

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "789dfd6427c6"
down_revision = "a8890016b39c"
branch_labels = ()
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "shortened_link_click",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("link_id", sa.String(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("client_ip", sa.String(), nullable=False),
        sa.Column("referer", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("medium", sa.String(), nullable=True),
        sa.Column("campaign", sa.String(), nullable=True),
        sa.Column("term", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["link_id"],
            ["shortened_link.code"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("shortened_link_click")
    # ### end Alembic commands ###
