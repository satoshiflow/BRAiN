-- PostgreSQL Initialization Script for pgvector Extension
-- Runs automatically on first container startup

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create Mage.ai metadata schema
CREATE SCHEMA IF NOT EXISTS mage_metadata;

-- Grant permissions to brain user
GRANT ALL PRIVILEGES ON SCHEMA mage_metadata TO brain;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mage_metadata TO brain;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA mage_metadata TO brain;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA mage_metadata
GRANT ALL PRIVILEGES ON TABLES TO brain;

ALTER DEFAULT PRIVILEGES IN SCHEMA mage_metadata
GRANT ALL PRIVILEGES ON SEQUENCES TO brain;

-- Verify installation
SELECT version();
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'pgvector extension installed successfully';
    RAISE NOTICE 'mage_metadata schema created successfully';
END $$;
