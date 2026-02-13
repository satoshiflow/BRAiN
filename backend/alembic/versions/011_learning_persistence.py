"""Add learning persistence

Revision ID: 011_learning_persistence
Revises: 009_skills_system
Create Date: 2025-02-12 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011_learning_persistence'
down_revision: Union[str, None] = '009_skills_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create learning module tables for PostgreSQL persistence:
    - learning_strategies: Adaptive behavior strategies with KARMA scoring
    - ab_experiments: A/B testing experiments with statistical evaluation
    - learning_metrics: Performance metrics time-series data
    """
    
    # Create learning_strategies table
    op.execute("""
        CREATE TABLE IF NOT EXISTS learning_strategies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            strategy_id VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            agent_id VARCHAR(100) NOT NULL,
            domain VARCHAR(50) NOT NULL DEFAULT 'general',
            parameters JSONB NOT NULL DEFAULT '{}',
            status VARCHAR(20) NOT NULL DEFAULT 'candidate',
            karma_score FLOAT NOT NULL DEFAULT 50.0,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            total_applications INTEGER NOT NULL DEFAULT 0,
            exploration_weight FLOAT NOT NULL DEFAULT 0.3,
            confidence FLOAT NOT NULL DEFAULT 0.0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    
    # Create indexes for learning_strategies
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategies_strategy_id ON learning_strategies (strategy_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategies_agent_id ON learning_strategies (agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategies_domain ON learning_strategies (domain);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategies_status ON learning_strategies (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategies_agent_domain ON learning_strategies (agent_id, domain);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategies_status_domain ON learning_strategies (status, domain);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_strategies_agent_status ON learning_strategies (agent_id, status);")
    
    # Create ab_experiments table
    op.execute("""
        CREATE TABLE IF NOT EXISTS ab_experiments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            experiment_id VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            agent_id VARCHAR(100) NOT NULL,
            domain VARCHAR(50) NOT NULL DEFAULT 'general',
            control_strategy_id VARCHAR(50) NOT NULL REFERENCES learning_strategies(strategy_id),
            control_traffic_weight FLOAT NOT NULL DEFAULT 0.5,
            control_sample_count INTEGER NOT NULL DEFAULT 0,
            control_success_count INTEGER NOT NULL DEFAULT 0,
            control_total_metric_value FLOAT NOT NULL DEFAULT 0.0,
            treatment_strategy_id VARCHAR(50) NOT NULL REFERENCES learning_strategies(strategy_id),
            treatment_traffic_weight FLOAT NOT NULL DEFAULT 0.5,
            treatment_sample_count INTEGER NOT NULL DEFAULT 0,
            treatment_success_count INTEGER NOT NULL DEFAULT 0,
            treatment_total_metric_value FLOAT NOT NULL DEFAULT 0.0,
            metric_type VARCHAR(20) NOT NULL DEFAULT 'success_rate',
            min_samples INTEGER NOT NULL DEFAULT 30,
            confidence_level FLOAT NOT NULL DEFAULT 0.95,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            winner VARCHAR(50),
            p_value FLOAT,
            effect_size FLOAT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    
    # Create indexes for ab_experiments
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_experiment_id ON ab_experiments (experiment_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_agent_id ON ab_experiments (agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_status ON ab_experiments (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_agent_status ON ab_experiments (agent_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_domain_status ON ab_experiments (domain, status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_status_created ON ab_experiments (status, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_control_strategy ON ab_experiments (control_strategy_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_treatment_strategy ON ab_experiments (treatment_strategy_id);")
    
    # Create learning_metrics table
    op.execute("""
        CREATE TABLE IF NOT EXISTS learning_metrics (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            metric_id VARCHAR(50) NOT NULL UNIQUE,
            agent_id VARCHAR(100) NOT NULL,
            metric_type VARCHAR(20) NOT NULL,
            value FLOAT NOT NULL,
            unit VARCHAR(20) NOT NULL DEFAULT '',
            tags JSONB NOT NULL DEFAULT '{}',
            timestamp TIMESTAMP NOT NULL,
            context JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    
    # Create indexes for learning_metrics
    op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_metric_id ON learning_metrics (metric_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_agent_id ON learning_metrics (agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_metric_type ON learning_metrics (metric_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON learning_metrics (timestamp);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_agent_type ON learning_metrics (agent_id, metric_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_agent_timestamp ON learning_metrics (agent_id, timestamp);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type_timestamp ON learning_metrics (metric_type, timestamp);")
    
    # Create update trigger for updated_at columns
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Add triggers for updated_at
    op.execute("""
        DROP TRIGGER IF EXISTS update_strategies_updated_at ON learning_strategies;
        CREATE TRIGGER update_strategies_updated_at
            BEFORE UPDATE ON learning_strategies
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS update_experiments_updated_at ON ab_experiments;
        CREATE TRIGGER update_experiments_updated_at
            BEFORE UPDATE ON ab_experiments
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """
    Drop learning module tables.
    """
    op.drop_table('learning_metrics', if_exists=True)
    op.drop_table('ab_experiments', if_exists=True)
    op.drop_table('learning_strategies', if_exists=True)
