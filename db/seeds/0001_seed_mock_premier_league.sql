-- Seed de DESARROLLO — Premier League (DATOS MOCK, NO REALES)
-- ⚠️ Todo lo insertado aquí lleva is_mock = true. No representa equipos ni
-- resultados verídicos. Sirve solo para ejercitar API y UI en Fase 1.
-- La UI DEBE mostrar un banner cuando una vista contenga filas con is_mock = true.

BEGIN;

INSERT INTO competition (sport_id, canonical_code, name, country, tier)
VALUES (1, 'ENG_PL', 'Premier League (mock)', 'England', 1)
ON CONFLICT (canonical_code) DO NOTHING;

INSERT INTO season (competition_id, label, start_date, end_date)
SELECT id, '2025-2026', DATE '2025-08-16', DATE '2026-05-24'
FROM competition WHERE canonical_code = 'ENG_PL'
ON CONFLICT (competition_id, label) DO NOTHING;

INSERT INTO team (sport_id, canonical_code, name, short_name, country) VALUES
    (1, 'ENG_ARS', 'Arsenal (mock)',            'ARS', 'England'),
    (1, 'ENG_CHE', 'Chelsea (mock)',            'CHE', 'England'),
    (1, 'ENG_LIV', 'Liverpool (mock)',          'LIV', 'England'),
    (1, 'ENG_MCI', 'Manchester City (mock)',    'MCI', 'England'),
    (1, 'ENG_MUN', 'Manchester United (mock)',  'MUN', 'England'),
    (1, 'ENG_TOT', 'Tottenham Hotspur (mock)',  'TOT', 'England'),
    (1, 'ENG_NEW', 'Newcastle United (mock)',   'NEW', 'England'),
    (1, 'ENG_AVL', 'Aston Villa (mock)',        'AVL', 'England')
ON CONFLICT (canonical_code) DO NOTHING;

-- Un par de partidos mock: uno finalizado, uno programado.
WITH c AS (SELECT id AS competition_id FROM competition WHERE canonical_code = 'ENG_PL'),
     s AS (SELECT se.id AS season_id FROM season se JOIN c ON se.competition_id = c.competition_id
           WHERE se.label = '2025-2026'),
     ars AS (SELECT id FROM team WHERE canonical_code = 'ENG_ARS'),
     che AS (SELECT id FROM team WHERE canonical_code = 'ENG_CHE'),
     liv AS (SELECT id FROM team WHERE canonical_code = 'ENG_LIV'),
     mci AS (SELECT id FROM team WHERE canonical_code = 'ENG_MCI')
INSERT INTO match (sport_id, competition_id, season_id, home_team_id, away_team_id,
                   kickoff_utc, status, home_score, away_score, is_mock)
SELECT 1, c.competition_id, s.season_id, (SELECT id FROM ars), (SELECT id FROM che),
       TIMESTAMPTZ '2025-08-16 14:00+00', 'finished', 2, 1, true
FROM c, s
UNION ALL
SELECT 1, c.competition_id, s.season_id, (SELECT id FROM liv), (SELECT id FROM mci),
       TIMESTAMPTZ '2026-06-27 14:00+00', 'scheduled', NULL, NULL, true
FROM c, s
ON CONFLICT DO NOTHING;

COMMIT;
