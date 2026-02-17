"""Add business and course factory tables

Revision ID: 007
Revises: 006
Create Date: 2026-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create business_processes table
    op.create_table(
        'business_processes',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(100)),
        sa.Column('trigger_type', sa.String(50)),
        sa.Column('trigger_config', postgresql.JSON()),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(100)),
        sa.Column('total_executions', sa.Integer(), default=0),
        sa.Column('successful_executions', sa.Integer(), default=0),
        sa.Column('failed_executions', sa.Integer(), default=0),
        sa.Column('avg_duration_seconds', sa.Float(), default=0.0),
    )
    op.create_index('idx_business_processes_category', 'business_processes', ['category'])
    op.create_index('idx_business_processes_enabled', 'business_processes', ['enabled'])

    # Create process_steps table
    op.create_table(
        'process_steps',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('process_id', sa.String(50), sa.ForeignKey('business_processes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('step_type', sa.String(50), nullable=False),
        sa.Column('action_type', sa.String(100)),
        sa.Column('action_config', postgresql.JSON()),
        sa.Column('condition', sa.Text()),
        sa.Column('on_success', sa.String(50)),
        sa.Column('on_failure', sa.String(50)),
        sa.Column('timeout_seconds', sa.Integer(), default=300),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('retry_delay_seconds', sa.Integer(), default=60),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_process_steps_process_id', 'process_steps', ['process_id'])
    op.create_index('idx_process_steps_step_number', 'process_steps', ['process_id', 'step_number'])

    # Create process_executions table
    op.create_table(
        'process_executions',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('process_id', sa.String(50), sa.ForeignKey('business_processes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('current_step_id', sa.String(50)),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('duration_seconds', sa.Float()),
        sa.Column('input_data', postgresql.JSON()),
        sa.Column('output_data', postgresql.JSON()),
        sa.Column('step_results', postgresql.JSON()),
        sa.Column('error_message', sa.Text()),
        sa.Column('error_step_id', sa.String(50)),
        sa.Column('triggered_by', sa.String(100)),
        sa.Column('trigger_source', sa.String(100)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_process_executions_process_id', 'process_executions', ['process_id'])
    op.create_index('idx_process_executions_status', 'process_executions', ['status'])
    op.create_index('idx_process_executions_created_at', 'process_executions', ['created_at'])

    # Create process_triggers table
    op.create_table(
        'process_triggers',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('process_id', sa.String(50), sa.ForeignKey('business_processes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('trigger_config', postgresql.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('last_triggered_at', sa.DateTime()),
        sa.Column('next_trigger_at', sa.DateTime()),
        sa.Column('total_triggers', sa.Integer(), default=0),
        sa.Column('successful_triggers', sa.Integer(), default=0),
        sa.Column('failed_triggers', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_process_triggers_process_id', 'process_triggers', ['process_id'])
    op.create_index('idx_process_triggers_enabled', 'process_triggers', ['enabled'])
    op.create_index('idx_process_triggers_next_trigger_at', 'process_triggers', ['next_trigger_at'])

    # Create course_templates table
    op.create_table(
        'course_templates',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(100)),
        sa.Column('difficulty_level', sa.String(50)),
        sa.Column('language', sa.String(10), default='en'),
        sa.Column('estimated_duration_hours', sa.Float()),
        sa.Column('prerequisites', postgresql.JSON()),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('published_at', sa.DateTime()),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('total_enrollments', sa.Integer(), default=0),
        sa.Column('completion_rate', sa.Float(), default=0.0),
        sa.Column('avg_rating', sa.Float(), default=0.0),
        sa.Column('total_reviews', sa.Integer(), default=0),
        sa.Column('is_free', sa.Boolean(), default=True),
        sa.Column('price', sa.Float(), default=0.0),
        sa.Column('currency', sa.String(10), default='EUR'),
        sa.Column('created_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('generated_by_ai', sa.Boolean(), default=False),
        sa.Column('generation_prompt', sa.Text()),
        sa.Column('ai_model', sa.String(100)),
    )
    op.create_index('idx_course_templates_category', 'course_templates', ['category'])
    op.create_index('idx_course_templates_status', 'course_templates', ['status'])
    op.create_index('idx_course_templates_difficulty', 'course_templates', ['difficulty_level'])

    # Create course_modules table
    op.create_table(
        'course_modules',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('course_id', sa.String(50), sa.ForeignKey('course_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('module_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('learning_objectives', postgresql.JSON()),
        sa.Column('estimated_duration_hours', sa.Float()),
        sa.Column('requires_quiz', sa.Boolean(), default=False),
        sa.Column('requires_project', sa.Boolean(), default=False),
        sa.Column('min_passing_score', sa.Float(), default=70.0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_course_modules_course_id', 'course_modules', ['course_id'])
    op.create_index('idx_course_modules_module_number', 'course_modules', ['course_id', 'module_number'])

    # Create lessons table
    op.create_table(
        'lessons',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('module_id', sa.String(50), sa.ForeignKey('course_modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lesson_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('lesson_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text()),
        sa.Column('video_url', sa.String(500)),
        sa.Column('duration_minutes', sa.Integer()),
        sa.Column('has_quiz', sa.Boolean(), default=False),
        sa.Column('quiz_questions', postgresql.JSON()),
        sa.Column('has_exercise', sa.Boolean(), default=False),
        sa.Column('exercise_config', postgresql.JSON()),
        sa.Column('is_required', sa.Boolean(), default=True),
        sa.Column('allows_skip', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_lessons_module_id', 'lessons', ['module_id'])
    op.create_index('idx_lessons_lesson_number', 'lessons', ['module_id', 'lesson_number'])

    # Create lesson_resources table
    op.create_table(
        'lesson_resources',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('lesson_id', sa.String(50), sa.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('file_url', sa.String(500)),
        sa.Column('file_size_bytes', sa.Integer()),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('external_url', sa.String(500)),
        sa.Column('is_downloadable', sa.Boolean(), default=True),
        sa.Column('requires_enrollment', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_lesson_resources_lesson_id', 'lesson_resources', ['lesson_id'])

    # Create course_enrollments table
    op.create_table(
        'course_enrollments',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('course_id', sa.String(50), sa.ForeignKey('course_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('enrolled_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('progress_percentage', sa.Float(), default=0.0),
        sa.Column('current_module_id', sa.String(50)),
        sa.Column('current_lesson_id', sa.String(50)),
        sa.Column('completed_lessons', postgresql.JSON()),
        sa.Column('total_quiz_score', sa.Float(), default=0.0),
        sa.Column('total_quizzes', sa.Integer(), default=0),
        sa.Column('avg_quiz_score', sa.Float(), default=0.0),
        sa.Column('total_time_spent_minutes', sa.Integer(), default=0),
        sa.Column('last_accessed_at', sa.DateTime()),
        sa.Column('certificate_issued', sa.Boolean(), default=False),
        sa.Column('certificate_issued_at', sa.DateTime()),
        sa.Column('certificate_url', sa.String(500)),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_course_enrollments_course_id', 'course_enrollments', ['course_id'])
    op.create_index('idx_course_enrollments_user_id', 'course_enrollments', ['user_id'])
    op.create_index('idx_course_enrollments_status', 'course_enrollments', ['status'])


def downgrade() -> None:
    # Drop all tables in reverse order (respecting foreign keys)
    op.drop_table('course_enrollments')
    op.drop_table('lesson_resources')
    op.drop_table('lessons')
    op.drop_table('course_modules')
    op.drop_table('course_templates')
    op.drop_table('process_triggers')
    op.drop_table('process_executions')
    op.drop_table('process_steps')
    op.drop_table('business_processes')
