TRUNCATE TABLE
    service_components,
    people,
    roles,
    teams,
    services,
    components
RESTART IDENTITY CASCADE;

COPY teams (id, name, archived_at, updated_at)
FROM '/data/teams.csv'
WITH (FORMAT csv, HEADER true);

COPY roles (id, name, grade, updated_at, archived_at)
FROM '/data/roles.csv'
WITH (FORMAT csv, HEADER true);

COPY people (
    id,
    name,
    email_address,
    location,
    employment_type,
    archived_at,
    updated_at,
    role_id,
    team_id,
    manager_id
)
FROM '/data/people.csv'
WITH (FORMAT csv, HEADER true);

COPY services (id, name, description, archived_at, updated_at, team_id)
FROM '/data/services.csv'
WITH (FORMAT csv, HEADER true);

COPY components (id, name, archived_at, updated_at)
FROM '/data/components.csv'
WITH (FORMAT csv, HEADER true);

COPY service_components (service_id, component_id)
FROM '/data/service_components.csv'
WITH (FORMAT csv, HEADER true);
