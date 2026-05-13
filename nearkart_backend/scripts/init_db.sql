-- NearKart Database Initialization
-- This runs automatically when PostgreSQL container starts for the first time

-- Enable PostGIS extension (required for geo queries)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Enable fuzzy text search (required for product/store search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
