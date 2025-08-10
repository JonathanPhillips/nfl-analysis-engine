-- Fix position data for players using seasonal rosters data
UPDATE players 
SET position = seasonal_rosters.position,
    jersey_number = COALESCE(players.jersey_number, seasonal_rosters.jersey_number)
FROM (
    SELECT DISTINCT ON (gsis_id) 
           gsis_id, position, jersey_number, season
    FROM seasonal_rosters 
    WHERE position IS NOT NULL 
          AND position != ''
          AND gsis_id IS NOT NULL
    ORDER BY gsis_id, season DESC
) AS seasonal_rosters
WHERE players.gsis_id = seasonal_rosters.gsis_id
  AND players.position IS NULL;

-- Show results
SELECT COUNT(*) as total_players, 
       COUNT(position) as players_with_position,
       ROUND((COUNT(position)::decimal / COUNT(*))*100, 1) as coverage_percent
FROM players;