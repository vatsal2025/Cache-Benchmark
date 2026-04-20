"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organisations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client_id", sa.String(64), unique=True, nullable=False),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("role_tier", sa.String(20), server_default="standard"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("gpu_hours_quota", sa.Integer, server_default="20"),
        sa.Column("concurrent_jobs_quota", sa.Integer, server_default="3"),
        sa.Column("tos_accepted", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_organisations_client_id", "organisations", ["client_id"])

    op.create_table(
        "captcha_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), server_default="1.0"),
        sa.Column("captcha_type", sa.String(50), nullable=False),
        sa.Column("category_set_size", sa.Integer, server_default="0"),
        sa.Column("occlusion_enabled", sa.Boolean, server_default="false"),
        sa.Column("occlusion_type", sa.String(20), server_default="none"),
        sa.Column("variation_count", sa.Integer, server_default="0"),
        sa.Column("challenge_format", sa.String(255), server_default=""),
        sa.Column("asset_path", sa.String(500), nullable=True),
        sa.Column("tags", postgresql.JSON, server_default="[]"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("category_diversity_score", sa.Float, server_default="0.0"),
        sa.Column("occlusion_score", sa.Float, server_default="0.0"),
        sa.Column("variation_density_score", sa.Float, server_default="0.0"),
        sa.Column("aggregate_guideline_score", sa.Float, server_default="0.0"),
        sa.Column("improvement_suggestions", postgresql.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_captcha_submissions_org_status", "captcha_submissions", ["org_id", "status"])

    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("control_captcha_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("captcha_submissions.id"), nullable=False),
        sa.Column("test_captcha_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("captcha_submissions.id"), nullable=False),
        sa.Column("population_segments", postgresql.JSON, server_default="{}"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("n_day_delay", sa.Integer, server_default="7"),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("backtest_enabled", sa.Boolean, server_default="false"),
        sa.Column("holdout_pct", sa.Integer, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_experiments_org_id", "experiments", ["org_id"])

    op.create_table(
        "attack_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("captcha_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("captcha_submissions.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=True),
        sa.Column("attack_type", sa.String(30), nullable=False),
        sa.Column("sample_size", sa.Integer, server_default="1000"),
        sa.Column("mode", sa.String(20), server_default="standard"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("asr_overall", sa.Float, nullable=True),
        sa.Column("asr_by_category", postgresql.JSON, nullable=True),
        sa.Column("error_breakdown", postgresql.JSON, nullable=True),
        sa.Column("avg_processing_time_ms", sa.Float, nullable=True),
        sa.Column("human_parity_score", sa.Float, nullable=True),
        sa.Column("model_version", sa.String(50), server_default="v1.0"),
        sa.Column("job_id", sa.String(100), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attack_runs_captcha_type", "attack_runs", ["captcha_id", "attack_type"])
    op.create_index("ix_attack_runs_status", "attack_runs", ["status"])

    op.create_table(
        "pas_labels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("group", sa.String(20), nullable=False),
        sa.Column("proxy_label", sa.String(10), nullable=False),
        sa.Column("proxy_probability", sa.Float, server_default="0.0"),
        sa.Column("human_label", sa.String(20), nullable=True),
        sa.Column("delay_days", sa.Integer, server_default="7"),
        sa.Column("model_version", sa.String(50), server_default="v1.0"),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pas_labels_exp_label", "pas_labels", ["experiment_id", "proxy_label"])

    op.create_table(
        "clearance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("group", sa.String(20), server_default="control"),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("step_id", sa.String(100), server_default=""),
        sa.Column("country", sa.String(10), server_default=""),
        sa.Column("device_type", sa.String(20), server_default="desktop"),
        sa.Column("account_age_days", sa.Integer, server_default="0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clearance_events_exp_id", "clearance_events", ["experiment_id"])
    op.create_index("ix_clearance_events_occurred_at", "clearance_events", ["occurred_at"])
    op.create_index("ix_clearance_events_exp_account", "clearance_events", ["experiment_id", "account_id"])

    op.create_table(
        "backtest_holdouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("captcha_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("captcha_submissions.id"), nullable=False),
        sa.Column("holdout_pct", sa.Integer, server_default="5"),
        sa.Column("baseline_bpas_prevalence", sa.Float, nullable=True),
        sa.Column("current_bpas_prevalence", sa.Float, nullable=True),
        sa.Column("bpas_history", postgresql.JSON, server_default="[]"),
        sa.Column("status", sa.String(20), server_default="monitoring"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "adaptation_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("holdout_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_holdouts.id"), nullable=False),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("baseline_bpas", sa.Float, nullable=False),
        sa.Column("current_bpas", sa.Float, nullable=False),
        sa.Column("drift_magnitude", sa.Float, nullable=False),
        sa.Column("nature", sa.String(100), server_default="BPAS_DRIFT"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_org_id", "audit_logs", ["actor_org_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    op.create_table(
        "experiment_scorecards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False, unique=True),
        sa.Column("control_clearance_rate", sa.Float, server_default="0.0"),
        sa.Column("control_gpas", sa.Float, server_default="0.0"),
        sa.Column("control_bpas", sa.Float, server_default="0.0"),
        sa.Column("control_epas", sa.Float, server_default="0.0"),
        sa.Column("control_asr_holistic", sa.Float, nullable=True),
        sa.Column("control_asr_modular", sa.Float, nullable=True),
        sa.Column("test_clearance_rate", sa.Float, server_default="0.0"),
        sa.Column("test_gpas", sa.Float, server_default="0.0"),
        sa.Column("test_bpas", sa.Float, server_default="0.0"),
        sa.Column("test_epas", sa.Float, server_default="0.0"),
        sa.Column("test_asr_holistic", sa.Float, nullable=True),
        sa.Column("test_asr_modular", sa.Float, nullable=True),
        sa.Column("clearance_rate_pvalue", sa.Float, nullable=True),
        sa.Column("bpas_pvalue", sa.Float, nullable=True),
        sa.Column("is_significant", sa.Boolean, server_default="false"),
        sa.Column("category_diversity_score", sa.Float, server_default="0.0"),
        sa.Column("occlusion_score", sa.Float, server_default="0.0"),
        sa.Column("variation_density_score", sa.Float, server_default="0.0"),
        sa.Column("recommendation", sa.String(50), server_default="INCONCLUSIVE"),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("segment_breakdown", postgresql.JSON, server_default="{}"),
        sa.Column("clearance_funnel", postgresql.JSON, server_default="{}"),
        sa.Column("model_version", sa.String(50), server_default="v1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "label_validation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("labels_count", sa.Integer, server_default="0"),
        sa.Column("sufficient_labels", sa.Boolean, server_default="false"),
        sa.Column("precision_gpas", sa.Float, server_default="0.0"),
        sa.Column("recall_gpas", sa.Float, server_default="0.0"),
        sa.Column("f1_gpas", sa.Float, server_default="0.0"),
        sa.Column("precision_bpas", sa.Float, server_default="0.0"),
        sa.Column("recall_bpas", sa.Float, server_default="0.0"),
        sa.Column("f1_bpas", sa.Float, server_default="0.0"),
        sa.Column("precision_epas", sa.Float, server_default="0.0"),
        sa.Column("recall_epas", sa.Float, server_default="0.0"),
        sa.Column("f1_epas", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("label_validation_results")
    op.drop_table("experiment_scorecards")
    op.drop_table("audit_logs")
    op.drop_table("adaptation_alerts")
    op.drop_table("backtest_holdouts")
    op.drop_table("clearance_events")
    op.drop_table("pas_labels")
    op.drop_table("attack_runs")
    op.drop_table("experiments")
    op.drop_table("captcha_submissions")
    op.drop_table("organisations")
