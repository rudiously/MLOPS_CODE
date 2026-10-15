"""initial CodeSentinel schema

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("repos", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("github_repo_id", sa.BigInteger(), nullable=True, unique=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("owner", sa.String(255), nullable=False), sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("github_user_id", sa.BigInteger(), nullable=True, unique=True), sa.Column("role", sa.String(50), nullable=False))
    op.create_table("repo_access", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repos.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("pr_scans", sa.Column("id", sa.String(36), primary_key=True), sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False), sa.Column("pr_number", sa.Integer(), nullable=False), sa.Column("commit_sha", sa.String(64), nullable=True), sa.Column("status", sa.String(30), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_pr_scans_repo_pr", "pr_scans", ["repo_id", "pr_number"])
    op.create_table("findings", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("scan_id", sa.String(36), sa.ForeignKey("pr_scans.id", ondelete="CASCADE"), nullable=False), sa.Column("file_path", sa.String(1024), nullable=False), sa.Column("line_number", sa.Integer(), nullable=False), sa.Column("cwe_id", sa.String(32), nullable=True), sa.Column("severity", sa.String(16), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("snippet", sa.Text(), nullable=False), sa.Column("model_version", sa.String(128), nullable=False))
    op.create_index("ix_findings_scan", "findings", ["scan_id"])
    op.create_index("ix_findings_severity", "findings", ["severity"])

def downgrade() -> None:
    op.drop_index("ix_findings_severity", table_name="findings"); op.drop_index("ix_findings_scan", table_name="findings"); op.drop_table("findings"); op.drop_index("ix_pr_scans_repo_pr", table_name="pr_scans"); op.drop_table("pr_scans"); op.drop_table("repo_access"); op.drop_table("users"); op.drop_table("repos")
