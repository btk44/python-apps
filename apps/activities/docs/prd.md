# Product Requirements Document: Activities Finder App

## 1. Overview

A simple application that stores a list of activities — places, activities,
and events — that people can go to. Users can browse the full list, filter
by distance from a reference location (e.g. their home), and filter by
target audience (kids, adults, all, etc.).

## 2. Goals

- Maintain a database of activities with enough metadata to support
  browsing and filtering.
- Let users find things near a specific location (e.g. within 5 km of home).
- Let users filter by who the activity is intended for.
- Support both permanent entries (parks, museums) and time-bound events
  (concerts) in the same system.

## 3. Core Features

### 3.1 Get the list
Return all activities, optionally with their associated targets and
categories.

### 3.2 Filter by location
Given a reference point (e.g. user's home coordinates) and a radius (e.g. 5
km), return only activities within that distance. Distance is calculated
using geographic (great-circle) distance, not straight-line Euclidean
distance.

### 3.3 Filter by target audience
Given a target (e.g. `kids`, `adults`, `all`), return only activities
tagged for that audience. An activity can be tagged with multiple
audiences (e.g. a park might suit both `kids` and `families`).

### 3.4 Filters can be combined
Location and target filters can be applied together in a single query.

## 4. Data Model

### 4.1 `activities` (core entity)

| Field              | Type                  | Notes                                              |
|--------------------|-----------------------|-----------------------------------------------------|
| id                 | SERIAL PK             |                                                     |
| name               | VARCHAR(255)          | Required                                           |
| description        | TEXT                  | Optional                                           |
| address            | VARCHAR(500)          | Optional, free text                                |
| country_code       | CHAR(2)                | Optional, ISO 3166-1 alpha-2 (e.g. `PL`, `US`)     |
| region             | VARCHAR(100)          | Optional (state/voivodeship/province)              |
| city               | VARCHAR(100)          | Optional                                           |
| location           | GEOGRAPHY(POINT,4326) | Required; single source of truth for coordinates, spatially indexed |
| activity_type      | VARCHAR(20)           | `place`, `activity`, or `event`                    |
| map_url            | VARCHAR(500)          | Optional                                           |
| website_url        | VARCHAR(500)          | Optional                                           |
| start_date         | TIMESTAMPTZ           | Optional; used for events (e.g. concerts)          |
| end_date           | TIMESTAMPTZ           | Optional; must be ≥ start_date if both are set     |
| is_active          | BOOLEAN               | Default `true`; used for soft delete               |
| version            | INT                   | Default `1`; auto-incremented on update, used for optimistic concurrency |
| created_at         | TIMESTAMP             | Auto-set                                           |
| updated_at         | TIMESTAMP             | Auto-updated via trigger                           |

### 4.2 `targets` (audience lookup)

| Field | Type          | Notes                                     |
|-------|---------------|--------------------------------------------|
| id    | SERIAL PK     |                                            |
| name  | VARCHAR(50)   | e.g. `kids`, `adults`, `all`, `families`, `seniors` |

### 4.3 `categories` (optional, for future filtering)

| Field | Type          | Notes                                          |
|-------|---------------|-------------------------------------------------|
| id    | SERIAL PK     |                                                 |
| name  | VARCHAR(100)  | e.g. `park`, `museum`, `concert`, `restaurant` |

### 4.4 Join tables

- `activity_targets` (activity_id, target_id) — many-to-many between
  activities and audiences.
- `activity_categories` (activity_id, category_id) — many-to-many between
  activities and categories.

### 4.5 Design decisions & rationale

- **Audience as a many-to-many relationship, not a single enum column** —
  an activity can serve more than one audience (e.g. `kids` + `families`).
- **No separate lat/lng columns** — `location` (a PostGIS `GEOGRAPHY(POINT)`)
  is the single source of truth for coordinates. Storing lat/lng separately
  would duplicate data already in `location` and require a trigger to keep
  them in sync. Plain lat/lng values can be extracted on read with
  `ST_Y(location::geometry)` / `ST_X(location::geometry)` when needed.
- **`is_active` for soft delete** — records are never hard-deleted;
  `is_active = false` marks an activity as removed while preserving
  history and avoiding broken foreign keys elsewhere (e.g. if favorites or
  bookings reference an activity later). Normal read queries filter on
  `is_active = true`, backed by a partial index.
- **`version` for optimistic concurrency control** — auto-incremented by a
  trigger on every `UPDATE`. Application code reads the current version,
  then includes `AND version = :expected_version` in its update statement;
  zero rows affected signals a conflicting concurrent edit.
- **Optional `start_date` / `end_date` live directly on `activities`**
  rather than in a separate table, since it's simpler for a small app.
  Non-events simply leave these fields `NULL`. If events later need many
  event-specific fields (ticket price, performer, recurrence), this can be
  split into a dedicated `event_details` table without much rework.
- **`country_code` / `region` / `city` as plain text columns**, not
  normalized lookup tables — good enough for filtering/browsing at this
  scale, with the option to normalize into `countries` / `regions` / `cities`
  tables later if consistency or autocomplete becomes a priority.
- **City/region/country filtering complements, not replaces, geo-distance
  filtering** — one supports coarse "browse by area," the other supports
  precise "near me" search.
- **`region`/`city` matching is case-insensitive exact match**
  (`lower(region) = lower(p_region)`), backed by expression indexes on
  `lower(region)`/`lower(city)` — this avoids casing mismatches (`Wroclaw`
  vs `wroclaw`) without the false-positive risk or index cost of a
  substring (`ILIKE '%...%'`) search.

## 5. Example Queries

All read queries below filter on `is_active = true` to respect soft deletes.

**Insert a new activity:**
```sql
INSERT INTO activities (name, description, location, activity_type, country_code, city)
VALUES (
    'Central Park',
    'A green space in the city center.',
    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
    'place',
    'PL',
    'Wrocław'
);
```

**Get full list with targets:**
```sql
SELECT a.*,
       ST_Y(a.location::geometry) AS latitude,
       ST_X(a.location::geometry) AS longitude,
       array_agg(DISTINCT t.name) AS targets
FROM activities a
LEFT JOIN activity_targets at2 ON at2.activity_id = a.id
LEFT JOIN targets t ON t.id = at2.target_id
WHERE a.is_active = true
GROUP BY a.id;
```

**Filter by distance (radius search):**
```sql
SELECT *, ST_Distance(location, ST_SetSRID(ST_MakePoint(:home_lng, :home_lat), 4326)::geography) AS distance_m
FROM activities
WHERE is_active = true
  AND ST_DWithin(location, ST_SetSRID(ST_MakePoint(:home_lng, :home_lat), 4326)::geography, 5000)
ORDER BY distance_m;
```

**Filter by target:**
```sql
SELECT a.*
FROM activities a
JOIN activity_targets at2 ON at2.activity_id = a.id
JOIN targets t ON t.id = at2.target_id
WHERE a.is_active = true
  AND t.name = 'kids';
```

**Combined: city + target:**
```sql
SELECT a.*, array_agg(DISTINCT t.name) AS targets
FROM activities a
LEFT JOIN activity_targets at2 ON at2.activity_id = a.id
LEFT JOIN targets t ON t.id = at2.target_id
WHERE a.is_active = true
  AND a.country_code = 'PL'
  AND lower(a.city) = lower('Wrocław')
  AND (t.name = 'kids' OR t.name IS NULL)
GROUP BY a.id;
```

**Soft delete an activity:**
```sql
UPDATE activities
SET is_active = false
WHERE id = :id;
```

**Update with optimistic concurrency check:**
```sql
-- Application first reads the row (including `version`), then submits:
UPDATE activities
SET name = :name, description = :description
WHERE id = :id AND version = :expected_version;

-- If this affects 0 rows, someone else updated the record first —
-- the application should reload and ask the user to retry.
```

## 5.1 `search_activities` function

A single Postgres function consolidates all search/filter use cases into
one call, so the application layer doesn't need to build dynamic SQL by
hand. All parameters are optional — pass `NULL` (or omit) to skip a filter.

| Parameter          | Type             | Behavior                                              |
|---------------------|------------------|--------------------------------------------------------|
| `p_name`            | TEXT             | Case-insensitive "contains" match on `name`            |
| `p_country_code`    | CHAR(2)          | Exact match                                             |
| `p_region`          | VARCHAR(100)     | Case-insensitive exact match                            |
| `p_city`            | VARCHAR(100)     | Case-insensitive exact match                            |
| `p_activity_type`   | VARCHAR(20)      | Exact match (`place` / `activity` / `event`)            |
| `p_target_names`    | TEXT[]           | Matches activities tagged with ANY of the given targets |
| `p_category_names`  | TEXT[]           | Matches activities tagged with ANY of the given categories |
| `p_start_date`      | TIMESTAMPTZ      | Start of search date range (open-ended if NULL)         |
| `p_end_date`        | TIMESTAMPTZ      | End of search date range (open-ended if NULL)           |
| `p_latitude`        | DOUBLE PRECISION | Reference point latitude                                |
| `p_longitude`       | DOUBLE PRECISION | Reference point longitude                               |
| `p_distance_m`      | DOUBLE PRECISION | Radius in meters; only applied if lat/lng also given    |
| `p_is_active`       | BOOLEAN          | Defaults to `true`; pass `NULL` to include inactive too |
| `p_limit`           | INT              | Pagination, defaults to 50                              |
| `p_offset`          | INT              | Pagination, defaults to 0                                |

**Date overlap logic:** if neither date parameter is given, no date
filtering happens. Activities with no `start_date` (e.g. permanent places
like parks) always match, since they have no schedule to compare.
Otherwise, the activity's `[start_date, end_date]` range must overlap the
given search range; open bounds are treated as -infinity/+infinity, and an
activity with a `start_date` but no `end_date` is treated as a
single-point-in-time event.

**Geo filtering:** distance filtering only applies when latitude, longitude,
*and* distance are all provided together. `distance_m` is still returned in
the result whenever a reference point is given, even without a distance
filter, so the client can sort/display distance without necessarily
restricting by it.

**Target/category filtering:** `p_target_names` and `p_category_names` use
`ANY`-match semantics — an activity matches if it's tagged with *at least
one* of the given values, not necessarily all of them. This matches typical
faceted-search UX (e.g. checking both "kids" and "families" should widen
results, not narrow them to activities tagged with both). Both are
implemented as `EXISTS` subqueries against the join tables, which only run
when a value is actually passed — unused filters are skipped at execution
time and add no meaningful overhead.

**Result ordering:** by distance from the reference point (if given), then
by `start_date`, then by `id` — with `LIMIT`/`OFFSET` pagination built in.

### Example calls

```sql
-- All active activities, no filters (first page)
SELECT * FROM search_activities();

-- Kids-friendly activities in Wrocław within 5 km of home
SELECT * FROM search_activities(
    p_city       => 'Wrocław',
    p_latitude   => 51.1079,
    p_longitude  => 17.0385,
    p_distance_m => 5000
);

-- Concerts happening in the next 30 days, name contains "jazz"
SELECT * FROM search_activities(
    p_name          => 'jazz',
    p_activity_type => 'event',
    p_start_date    => now(),
    p_end_date      => now() + interval '30 days'
);

-- Museums or parks, suitable for kids or families
SELECT * FROM search_activities(
    p_category_names => ARRAY['museum', 'park'],
    p_target_names   => ARRAY['kids', 'families']
);

-- Second page of results, 20 per page
SELECT * FROM search_activities(p_limit => 20, p_offset => 20);
```

### Performance notes

The number of optional scalar parameters (name, country, region, city,
activity type, dates, is_active) has negligible cost — each is a simple
`IS NULL OR ...` check evaluated in nanoseconds per row, regardless of how
many are added. The target/category filters are more expensive in kind
(they require a join against `activity_targets`/`activity_categories`), but:

- They're skipped entirely via short-circuit evaluation when their
  parameter is `NULL`.
- When used, they run as indexed `EXISTS` lookups scoped by `activity_id`
  (backed by `idx_activity_targets_target_id` /
  `idx_activity_categories_category_id`), not full table scans.
- Postgres' planner generally applies cheaper filters (exact matches on
  `city`, `country_code`, `activity_type`) before the more expensive
  `EXISTS` checks, so by the time target/category filtering runs, the
  candidate row set is usually already small.

Net effect: adding more optional parameters to this function is safe from a
performance standpoint. The cost scales with how selective your filters are
and how large the matching result set is — not with the number of
parameters the function accepts.

**Total counts and pagination:** adding a total-match count to this
function (e.g. via `count(*) OVER()`) would force Postgres to evaluate
every matching row instead of stopping early once `p_limit` rows are found,
which is more expensive on broad, unfiltered searches. If an exact total is
needed, prefer a separate `count_activities()` function mirroring the same
`WHERE` clause (called only when the UI actually needs a total), or use a
"fetch limit+1" trick to detect "more results exist" without a full count.

## 6. Technical Stack (assumed)

- **Database:** PostgreSQL with the PostGIS extension for geospatial queries.
- **Alternative:** If PostGIS is unavailable (e.g. SQLite), distance
  filtering can fall back to a Haversine formula in SQL or application code,
  at the cost of index-backed performance.

## 7. Out of Scope (for now)

- User accounts / saved favorites.
- Normalized geography tables (countries/regions/cities as separate entities).
- Recurring events / ticketing details.
- Reviews or ratings.
- Multi-language content.
- Full-text search across `description`.
- Configurable sort order (`p_sort_by`) on `search_activities`.
- A dedicated `count_activities()` function for exact total-match counts.

## 8. Open Questions

- Should "all" as a target mean an explicit tag, or the absence of any
  target tag (i.e. untagged = visible to everyone)?
- Do we need a dedicated `event_details` table now, or is deferring that
  split still the right call once real event data starts coming in?
- What's the primary client — a web app, mobile app, or both — since that
  affects API design going forward?
- Is an exact total result count needed for pagination UI, or is
  "load more" / "50+ results" sufficient?

## 9. Deliverables So Far

- `schema.sql` — full PostgreSQL + PostGIS schema: `activities` table (with
  constraints, `is_active` soft-delete and `version` optimistic-concurrency
  columns), `targets`/`categories` lookup tables, `activity_targets`/
  `activity_categories` join tables, a trigger keeping `updated_at`/
  `version` current on update, indexes, seed data, and a
  `search_activities()` function consolidating all filter/search use
  cases, including target and category (ANY-match) filtering.