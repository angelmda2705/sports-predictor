-- Migración inicial — sports-predictor (Fase 1)
-- Esquema base del MVP. Espejo SQL del diseño en docs/DOCUMENTO_TECNICO_MVP.md §5.
-- En Fase 2 esto se gestiona con Alembic; aquí se versiona el DDL de referencia.
--
-- Convenciones: snake_case, claves surrogate + clave natural única, timestamptz en UTC.
-- Toda tabla con datos de proveedor externo lleva is_mock para etiquetar mock data.

BEGIN;

-- ─────────────────────────── Catálogo deportivo ───────────────────────────
CREATE TABLE sport (
    id            smallint PRIMARY KEY,
    code          text UNIQUE NOT NULL,
    name          text NOT NULL
);
INSERT INTO sport (id, code, name) VALUES
    (1, 'soccer', 'Fútbol soccer'),
    (2, 'american_football', 'Fútbol americano');

CREATE TABLE competition (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport_id        smallint NOT NULL REFERENCES sport(id),
    canonical_code  text UNIQUE NOT NULL,
    name            text NOT NULL,
    country         text,
    tier            smallint,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE season (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    competition_id  bigint NOT NULL REFERENCES competition(id),
    label           text NOT NULL,
    start_date      date,
    end_date        date,
    UNIQUE (competition_id, label)
);

CREATE TABLE team (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport_id        smallint NOT NULL REFERENCES sport(id),
    canonical_code  text UNIQUE NOT NULL,
    name            text NOT NULL,
    short_name      text,
    country         text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE venue (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            text NOT NULL,
    city            text,
    country         text,
    latitude        numeric(9,6),
    longitude       numeric(9,6),
    surface         text,
    is_dome         boolean
);

CREATE TABLE player (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport_id        smallint NOT NULL REFERENCES sport(id),
    canonical_code  text UNIQUE NOT NULL,
    full_name       text NOT NULL,
    position        text,
    team_id         bigint REFERENCES team(id)
);

CREATE TABLE provider_entity_map (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider        text NOT NULL,
    entity_type     text NOT NULL,
    provider_ref    text NOT NULL,
    canonical_id    bigint NOT NULL,
    UNIQUE (provider, entity_type, provider_ref)
);

-- ─────────────────────────── Partidos y stats ───────────────────────────
CREATE TABLE match (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport_id         smallint NOT NULL REFERENCES sport(id),
    competition_id   bigint NOT NULL REFERENCES competition(id),
    season_id        bigint NOT NULL REFERENCES season(id),
    home_team_id     bigint NOT NULL REFERENCES team(id),
    away_team_id     bigint NOT NULL REFERENCES team(id),
    venue_id         bigint REFERENCES venue(id),
    kickoff_utc      timestamptz NOT NULL,
    stage            text,
    status           text NOT NULL,
    home_score       smallint,
    away_score       smallint,
    home_score_ht    smallint,
    away_score_ht    smallint,
    data_snapshot_id text,
    is_mock          boolean NOT NULL DEFAULT false,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (competition_id, season_id, home_team_id, away_team_id, kickoff_utc),
    CONSTRAINT chk_distinct_teams CHECK (home_team_id <> away_team_id)
);
CREATE INDEX idx_match_kickoff ON match (kickoff_utc);
CREATE INDEX idx_match_status ON match (status);

CREATE TABLE match_team_stats (
    match_id        bigint NOT NULL REFERENCES match(id),
    team_id         bigint NOT NULL REFERENCES team(id),
    is_home         boolean NOT NULL,
    xg              numeric(5,2),
    shots           smallint,
    shots_on_target smallint,
    possession      numeric(4,1),
    corners         smallint,
    yellow_cards    smallint,
    red_cards       smallint,
    epa_per_play    numeric(6,3),
    success_rate    numeric(5,3),
    yards           smallint,
    pass_yards      smallint,
    rush_yards      smallint,
    turnovers       smallint,
    sacks           smallint,
    third_down_pct  numeric(5,3),
    redzone_pct     numeric(5,3),
    PRIMARY KEY (match_id, team_id)
);

CREATE TABLE injury (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id       bigint NOT NULL REFERENCES player(id),
    team_id         bigint NOT NULL REFERENCES team(id),
    status          text NOT NULL,
    reported_at     timestamptz NOT NULL,
    source          text,
    is_mock         boolean NOT NULL DEFAULT false
);
CREATE INDEX idx_injury_reported ON injury (team_id, reported_at);

CREATE TABLE odds (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id        bigint NOT NULL REFERENCES match(id),
    bookmaker       text NOT NULL,
    market          text NOT NULL,
    captured_at     timestamptz NOT NULL,
    payload         jsonb NOT NULL,
    is_mock         boolean NOT NULL DEFAULT false
);

-- ──────────────── Feature store, modelos y predicciones ────────────────
CREATE TABLE feature_set (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version         text UNIQUE NOT NULL,
    sport_id        smallint NOT NULL REFERENCES sport(id),
    spec            jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE match_features (
    match_id        bigint NOT NULL REFERENCES match(id),
    feature_set_id  bigint NOT NULL REFERENCES feature_set(id),
    computed_at     timestamptz NOT NULL,
    features        jsonb NOT NULL,
    PRIMARY KEY (match_id, feature_set_id)
);

CREATE TABLE model_version (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            text NOT NULL,
    version         text NOT NULL,
    sport_id        smallint NOT NULL REFERENCES sport(id),
    target          text NOT NULL,
    algorithm       text NOT NULL,
    feature_set_id  bigint REFERENCES feature_set(id),
    mlflow_run_id   text,
    artifact_uri    text,
    trained_at      timestamptz NOT NULL,
    train_window    daterange,
    metrics         jsonb,
    calibration     jsonb,
    is_active       boolean NOT NULL DEFAULT false,
    UNIQUE (name, version)
);

CREATE TABLE prediction (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id         bigint NOT NULL REFERENCES match(id),
    model_version_id bigint NOT NULL REFERENCES model_version(id),
    data_snapshot_id text NOT NULL,
    seed             integer,
    created_at       timestamptz NOT NULL DEFAULT now(),
    prob_home        numeric(6,5),
    prob_draw        numeric(6,5),
    prob_away        numeric(6,5),
    exp_home_goals   numeric(5,2),
    exp_away_goals   numeric(5,2),
    exp_spread       numeric(5,2),
    exp_total        numeric(5,2),
    scoreline_dist   jsonb,
    market_probs     jsonb,
    confidence       numeric(6,5),
    confidence_band  text,
    data_quality     jsonb,
    explanation      jsonb,
    UNIQUE (match_id, model_version_id)
);

CREATE TABLE prediction_history (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    prediction_id   bigint NOT NULL REFERENCES prediction(id),
    snapshot        jsonb NOT NULL,
    recorded_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE prediction_outcome (
    prediction_id    bigint PRIMARY KEY REFERENCES prediction(id),
    resolved_at      timestamptz NOT NULL,
    actual_result    text,
    brier            numeric(8,6),
    log_loss         numeric(10,6),
    abs_error_spread numeric(6,2),
    abs_error_total  numeric(6,2),
    correct_pick     boolean
);

-- ──────────────── Usuarios, suscripciones y auditoría ────────────────
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE app_user (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           citext UNIQUE NOT NULL,
    password_hash   text NOT NULL,
    role            text NOT NULL DEFAULT 'user',
    plan            text NOT NULL DEFAULT 'free',
    email_verified  boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    deleted_at      timestamptz
);

CREATE TABLE refresh_token (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         bigint NOT NULL REFERENCES app_user(id),
    token_hash      text NOT NULL,
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz,
    rotated_from    bigint REFERENCES refresh_token(id)
);

CREATE TABLE favorite (
    user_id         bigint NOT NULL REFERENCES app_user(id),
    entity_type     text NOT NULL,
    entity_id       bigint NOT NULL,
    PRIMARY KEY (user_id, entity_type, entity_id)
);

CREATE TABLE audit_log (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_user_id   bigint REFERENCES app_user(id),
    action          text NOT NULL,
    target          text,
    ip              inet,
    metadata        jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE provider_run (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider        text NOT NULL,
    run_type        text NOT NULL,
    status          text NOT NULL,
    snapshot_id     text,
    rows_ingested   integer,
    started_at      timestamptz NOT NULL,
    finished_at     timestamptz,
    error           text
);

COMMIT;
