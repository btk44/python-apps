-- ============================================================
-- Activities / Places / Events database schema
-- PostgreSQL + PostGIS
-- ============================================================

-- ------------------------------------------------------------
-- 0. Extensions
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS postgis;

-- ------------------------------------------------------------
-- 1. Lookup tables
-- ------------------------------------------------------------

CREATE TABLE targets (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL   -- 'kids', 'adults', 'all', 'families', 'seniors', ...
);

CREATE TABLE categories (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL  -- 'park', 'museum', 'concert', 'restaurant', ...
);

-- ------------------------------------------------------------
-- 2. Core table: activities
-- ------------------------------------------------------------

CREATE TABLE activities (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(255) NOT NULL,
    description      TEXT,

    -- Free-text address plus structured location fields
    address          VARCHAR(500),
    country_code     CHAR(2),
    region           VARCHAR(100),
    city             VARCHAR(100),

    -- Coordinates (single source of truth, used for all spatial queries)
    location         GEOGRAPHY(POINT, 4326) NOT NULL,

    -- Type of entry
    activity_type    VARCHAR(20) NOT NULL DEFAULT 'place', -- 'place', 'activity', 'event'

    -- Optional links
    map_url          VARCHAR(500),
    website_url      VARCHAR(500),

    -- Optional scheduling (mainly for events, e.g. concerts)
    start_date       TIMESTAMPTZ,
    end_date         TIMESTAMPTZ,

    -- Soft delete + optimistic concurrency control
    is_active        BOOLEAN NOT NULL DEFAULT true,
    version          INT NOT NULL DEFAULT 1,

    created_at       TIMESTAMP DEFAULT now(),
    updated_at       TIMESTAMP DEFAULT now(),

    CONSTRAINT chk_activity_type CHECK (activity_type IN ('place', 'activity', 'event')),
    CONSTRAINT chk_country_code CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$'),
    CONSTRAINT chk_map_url CHECK (map_url IS NULL OR map_url ~ '^https?://'),
    CONSTRAINT chk_website_url CHECK (website_url IS NULL OR website_url ~ '^https?://'),
    CONSTRAINT chk_date_order CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

-- ------------------------------------------------------------
-- 3. Join tables (many-to-many)
-- ------------------------------------------------------------

CREATE TABLE activity_targets (
    activity_id INT REFERENCES activities(id) ON DELETE CASCADE,
    target_id   INT REFERENCES targets(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, target_id)
);

CREATE TABLE activity_categories (
    activity_id INT REFERENCES activities(id) ON DELETE CASCADE,
    category_id INT REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, category_id)
);

-- ------------------------------------------------------------
-- 4. Trigger: keep `updated_at` and `version` current on every update
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    NEW.version := OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_activities_set_updated_at
BEFORE UPDATE ON activities
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- ------------------------------------------------------------
-- 5. Indexes
-- ------------------------------------------------------------

-- Spatial index for radius / distance queries
CREATE INDEX idx_activities_location ON activities USING GIST (location);

-- Location filters (country / region / city)
CREATE INDEX idx_activities_country ON activities (country_code);
CREATE INDEX idx_activities_region_lower ON activities (lower(region));
CREATE INDEX idx_activities_city_lower ON activities (lower(city));
CREATE INDEX idx_activities_country_region_city ON activities (country_code, lower(region), lower(city));

-- Event date filtering ("upcoming events")
CREATE INDEX idx_activities_start_date ON activities (start_date) WHERE start_date IS NOT NULL;

-- Type filtering (place / activity / event)
CREATE INDEX idx_activities_activity_type ON activities (activity_type);

-- Soft delete: most queries only care about active rows
CREATE INDEX idx_activities_is_active ON activities (is_active) WHERE is_active = true;

-- Join table lookups
CREATE INDEX idx_activity_targets_target_id ON activity_targets (target_id);
CREATE INDEX idx_activity_categories_category_id ON activity_categories (category_id);

-- ------------------------------------------------------------
-- 6. Seed data for lookup tables (optional, adjust as needed)
-- ------------------------------------------------------------

INSERT INTO targets (name) VALUES
    ('kids'),
    ('adults'),
    ('all'),
    ('families'),
    ('seniors')
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (name) VALUES
    ('park'),
    ('museum'),
    ('concert'),
    ('restaurant'),
    ('hiking'),
    ('playground')
ON CONFLICT (name) DO NOTHING;

-- ------------------------------------------------------------
-- 7. Search function
-- ------------------------------------------------------------
-- All parameters are optional (default NULL / true). Passing NULL for a
-- given filter means "don't filter on this."
--
-- Date overlap logic:
--   - If neither p_start_date nor p_end_date is given, no date filtering is applied.
--   - Activities with no start_date (non-scheduled, e.g. parks) always match any date filter.
--   - Otherwise, the activity's [start_date, end_date] range must overlap the
--     search range [p_start_date, p_end_date]. Open-ended bounds (NULL) are
--     treated as -infinity / +infinity. An activity with no end_date is treated
--     as a single-point-in-time event on start_date.
--
-- Geo filtering:
--   - Only applied when p_latitude, p_longitude AND p_distance_m are all provided.
--   - distance_m in the result is populated whenever p_latitude/p_longitude
--     are given, regardless of whether a distance filter was applied.
--
-- Target/category filtering:
--   - p_target_names / p_category_names use ANY-match semantics: an activity
--     matches if it is tagged with at least one of the given values.
--   - Implemented as EXISTS subqueries; skipped entirely when their
--     parameter is NULL.
--
-- Results are ordered by distance (if a reference point was given), then by
-- start_date, then by id, and support simple pagination via p_limit/p_offset.

CREATE OR REPLACE FUNCTION search_activities(
    p_name            TEXT             DEFAULT NULL,
    p_country_code    CHAR(2)          DEFAULT NULL,
    p_region          VARCHAR(100)     DEFAULT NULL,
    p_city            VARCHAR(100)     DEFAULT NULL,
    p_activity_type   VARCHAR(20)      DEFAULT NULL,
    p_target_names    TEXT[]           DEFAULT NULL,
    p_category_names  TEXT[]           DEFAULT NULL,
    p_start_date      TIMESTAMPTZ      DEFAULT NULL,
    p_end_date        TIMESTAMPTZ      DEFAULT NULL,
    p_latitude        DOUBLE PRECISION DEFAULT NULL,
    p_longitude       DOUBLE PRECISION DEFAULT NULL,
    p_distance_m      DOUBLE PRECISION DEFAULT NULL,
    p_is_active       BOOLEAN          DEFAULT true,
    p_limit           INT              DEFAULT 50,
    p_offset          INT              DEFAULT 0
)
RETURNS TABLE (
    id               INT,
    name             VARCHAR,
    description      TEXT,
    address          VARCHAR,
    country_code     CHAR(2),
    region           VARCHAR,
    city             VARCHAR,
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    activity_type    VARCHAR,
    map_url          VARCHAR,
    website_url      VARCHAR,
    start_date       TIMESTAMPTZ,
    end_date         TIMESTAMPTZ,
    is_active        BOOLEAN,
    version          INT,
    distance_m       DOUBLE PRECISION,
    targets          TEXT[],
    categories       TEXT[]
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    SELECT
        a.id,
        a.name,
        a.description,
        a.address,
        a.country_code,
        a.region,
        a.city,
        ST_Y(a.location::geometry) AS latitude,
        ST_X(a.location::geometry) AS longitude,
        a.activity_type,
        a.map_url,
        a.website_url,
        a.start_date,
        a.end_date,
        a.is_active,
        a.version,
        CASE
            WHEN p_latitude IS NOT NULL AND p_longitude IS NOT NULL THEN
                ST_Distance(
                    a.location,
                    ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326)::geography
                )
            ELSE NULL
        END AS distance_m,
        t.targets,
        c.categories
    FROM activities a
    LEFT JOIN LATERAL (
        SELECT array_agg(tg.name) AS targets
        FROM activity_targets at2
        JOIN targets tg ON tg.id = at2.target_id
        WHERE at2.activity_id = a.id
    ) t ON true
    LEFT JOIN LATERAL (
        SELECT array_agg(cat.name) AS categories
        FROM activity_categories ac2
        JOIN categories cat ON cat.id = ac2.category_id
        WHERE ac2.activity_id = a.id
    ) c ON true
    WHERE
        (p_is_active IS NULL OR a.is_active = p_is_active)
        AND (p_name IS NULL OR a.name ILIKE '%' || p_name || '%')
        AND (p_country_code IS NULL OR a.country_code = p_country_code)
        AND (p_region IS NULL OR lower(a.region) = lower(p_region))
        AND (p_city IS NULL OR lower(a.city) = lower(p_city))
        AND (p_activity_type IS NULL OR a.activity_type = p_activity_type)
        AND (
            p_target_names IS NULL
            OR EXISTS (
                SELECT 1
                FROM activity_targets at3
                JOIN targets tg3 ON tg3.id = at3.target_id
                WHERE at3.activity_id = a.id
                  AND tg3.name = ANY(p_target_names)
            )
        )
        AND (
            p_category_names IS NULL
            OR EXISTS (
                SELECT 1
                FROM activity_categories ac3
                JOIN categories cat3 ON cat3.id = ac3.category_id
                WHERE ac3.activity_id = a.id
                  AND cat3.name = ANY(p_category_names)
            )
        )
        AND (
            (p_start_date IS NULL AND p_end_date IS NULL)
            OR a.start_date IS NULL
            OR (
                a.start_date <= COALESCE(p_end_date, 'infinity'::timestamptz)
                AND COALESCE(a.end_date, a.start_date) >= COALESCE(p_start_date, '-infinity'::timestamptz)
            )
        )
        AND (
            p_latitude IS NULL OR p_longitude IS NULL OR p_distance_m IS NULL
            OR ST_DWithin(
                a.location,
                ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326)::geography,
                p_distance_m
            )
        )
    ORDER BY
        CASE
            WHEN p_latitude IS NOT NULL AND p_longitude IS NOT NULL THEN
                ST_Distance(
                    a.location,
                    ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326)::geography
                )
        END ASC NULLS LAST,
        a.start_date ASC NULLS LAST,
        a.id
    LIMIT p_limit
    OFFSET p_offset;
$$;