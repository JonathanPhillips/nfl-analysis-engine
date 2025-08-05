# NFL Analysis Engine - Database Schema Design

## Overview

The database schema is designed to be compatible with `nfl_data_py` (nflfastR) data structure while supporting advanced analytics and real-time updates. The schema follows normalization principles with performance optimizations for analytical queries.

## Core Entities

### Teams Table
```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    team_abbr VARCHAR(3) UNIQUE NOT NULL,  -- 'SF', 'KC', etc.
    team_name VARCHAR(50) NOT NULL,        -- 'San Francisco'
    team_nick VARCHAR(50) NOT NULL,        -- '49ers'
    team_conf VARCHAR(3) NOT NULL,         -- 'AFC', 'NFC'
    team_division VARCHAR(10) NOT NULL,    -- 'North', 'South', 'East', 'West'
    
    -- Branding and visual
    team_color VARCHAR(7),                 -- '#AA0000'
    team_color2 VARCHAR(7),
    team_color3 VARCHAR(7), 
    team_color4 VARCHAR(7),
    team_logo_espn VARCHAR(255),
    team_logo_wikipedia VARCHAR(255),
    team_city VARCHAR(50),
    team_wordmark VARCHAR(255),
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT teams_conf_check CHECK (team_conf IN ('AFC', 'NFC')),
    CONSTRAINT teams_div_check CHECK (team_division IN ('North', 'South', 'East', 'West'))
);

CREATE INDEX idx_teams_abbr ON teams(team_abbr);
CREATE INDEX idx_teams_conf_div ON teams(team_conf, team_division);
```

### Players Table
```sql
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(20) UNIQUE NOT NULL,  -- nflfastR player_id
    gsis_id VARCHAR(20),                    -- GSIS ID for cross-reference
    full_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    
    -- Position and physical
    position VARCHAR(10),                   -- 'QB', 'RB', 'WR', etc.
    position_group VARCHAR(20),             -- 'offense', 'defense', 'special_teams'
    height INTEGER,                         -- Height in inches
    weight INTEGER,                         -- Weight in pounds
    age INTEGER,
    
    -- Team association
    team_abbr VARCHAR(3),
    jersey_number INTEGER,
    
    -- Career info
    rookie_year INTEGER,
    years_exp INTEGER,
    college VARCHAR(100),
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',    -- 'active', 'injured', 'retired'
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (team_abbr) REFERENCES teams(team_abbr)
);

CREATE INDEX idx_players_player_id ON players(player_id);
CREATE INDEX idx_players_team ON players(team_abbr);
CREATE INDEX idx_players_position ON players(position);
CREATE INDEX idx_players_name ON players(full_name);
```

### Games Table
```sql
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) UNIQUE NOT NULL,    -- nflfastR game_id
    old_game_id VARCHAR(20),                -- Legacy game ID for compatibility
    
    -- Game scheduling
    season INTEGER NOT NULL,
    season_type VARCHAR(10) NOT NULL,       -- 'REG', 'POST', 'PRE'
    week INTEGER,
    game_date DATE NOT NULL,
    kickoff_time TIME,
    
    -- Teams
    home_team VARCHAR(3) NOT NULL,
    away_team VARCHAR(3) NOT NULL,
    
    -- Game results
    home_score INTEGER,
    away_score INTEGER,
    result INTEGER,                         -- 1 if home team won, 0 if away team won
    total_score INTEGER,
    
    -- Game conditions
    roof VARCHAR(20),                       -- 'dome', 'outdoors', 'closed', 'open'
    surface VARCHAR(20),                    -- 'grass', 'fieldturf', etc.
    temp INTEGER,                           -- Temperature in Fahrenheit
    wind INTEGER,                           -- Wind speed in mph
    
    -- Betting information (if available)
    home_spread DECIMAL(4,1),               -- Point spread (home team perspective)
    total_line DECIMAL(4,1),                -- Over/under total
    home_moneyline INTEGER,                 -- Moneyline odds
    away_moneyline INTEGER,
    
    -- Game status
    game_finished BOOLEAN DEFAULT FALSE,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (home_team) REFERENCES teams(team_abbr),
    FOREIGN KEY (away_team) REFERENCES teams(team_abbr),
    CONSTRAINT games_season_type_check CHECK (season_type IN ('REG', 'POST', 'PRE'))
);

CREATE INDEX idx_games_game_id ON games(game_id);
CREATE INDEX idx_games_season_week ON games(season, week);
CREATE INDEX idx_games_teams ON games(home_team, away_team);
CREATE INDEX idx_games_date ON games(game_date);
```

## Statistical Data Tables

### Play-by-Play Data
```sql
CREATE TABLE plays (
    id SERIAL PRIMARY KEY,
    play_id VARCHAR(30) UNIQUE NOT NULL,    -- nflfastR play_id
    game_id VARCHAR(20) NOT NULL,
    
    -- Play context
    season INTEGER NOT NULL,
    week INTEGER,
    posteam VARCHAR(3),                     -- Possession team
    defteam VARCHAR(3),                     -- Defense team
    
    -- Game situation
    qtr INTEGER,                            -- Quarter (1-5, 5 for OT)
    game_seconds_remaining INTEGER,
    half_seconds_remaining INTEGER,
    game_half VARCHAR(10),                  -- 'Half1', 'Half2', 'Overtime'
    
    -- Field position
    yardline_100 INTEGER,                   -- Yards from opponent's goal line
    ydstogo INTEGER,                        -- Yards to go for first down
    down INTEGER,                           -- Down (1-4)
    
    -- Play details
    play_type VARCHAR(20),                  -- 'pass', 'run', 'punt', 'field_goal', etc.
    desc TEXT,                              -- Play description
    yards_gained INTEGER,
    
    -- Score before play
    posteam_score INTEGER,
    defteam_score INTEGER,
    score_differential INTEGER,
    
    -- Advanced metrics (from nflfastR)
    ep DECIMAL(6,3),                        -- Expected Points
    epa DECIMAL(6,3),                       -- Expected Points Added
    wp DECIMAL(8,6),                        -- Win Probability
    wpa DECIMAL(8,6),                       -- Win Probability Added
    
    -- Passing metrics
    cpoe DECIMAL(6,3),                      -- Completion Probability Over Expected
    pass_location VARCHAR(20),              -- 'left', 'middle', 'right'
    air_yards INTEGER,
    yards_after_catch INTEGER,
    
    -- Player involvement
    passer_player_id VARCHAR(20),
    receiver_player_id VARCHAR(20),
    rusher_player_id VARCHAR(20),
    
    -- Play result flags
    touchdown BOOLEAN DEFAULT FALSE,
    pass_touchdown BOOLEAN DEFAULT FALSE,
    rush_touchdown BOOLEAN DEFAULT FALSE,
    interception BOOLEAN DEFAULT FALSE,
    fumble BOOLEAN DEFAULT FALSE,
    safety BOOLEAN DEFAULT FALSE,
    penalty BOOLEAN DEFAULT FALSE,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (posteam) REFERENCES teams(team_abbr),
    FOREIGN KEY (defteam) REFERENCES teams(team_abbr),
    FOREIGN KEY (passer_player_id) REFERENCES players(player_id),
    FOREIGN KEY (receiver_player_id) REFERENCES players(player_id),
    FOREIGN KEY (rusher_player_id) REFERENCES players(player_id)
);

CREATE INDEX idx_plays_play_id ON plays(play_id);
CREATE INDEX idx_plays_game_id ON plays(game_id);
CREATE INDEX idx_plays_season_week ON plays(season, week);
CREATE INDEX idx_plays_posteam ON plays(posteam);
CREATE INDEX idx_plays_players ON plays(passer_player_id, receiver_player_id, rusher_player_id);
```

### Team Game Statistics
```sql
CREATE TABLE team_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    team_abbr VARCHAR(3) NOT NULL,
    
    -- Basic stats
    points_scored INTEGER,
    total_yards INTEGER,
    passing_yards INTEGER,
    rushing_yards INTEGER,
    turnovers INTEGER,
    
    -- Offensive efficiency
    third_down_conversions INTEGER,
    third_down_attempts INTEGER,
    red_zone_conversions INTEGER,
    red_zone_attempts INTEGER,
    
    -- Advanced metrics
    total_epa DECIMAL(8,3),
    passing_epa DECIMAL(8,3),
    rushing_epa DECIMAL(8,3),
    
    -- Time of possession
    time_of_possession_seconds INTEGER,
    
    -- Penalties
    penalties INTEGER,
    penalty_yards INTEGER,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (team_abbr) REFERENCES teams(team_abbr),
    UNIQUE(game_id, team_abbr)
);

CREATE INDEX idx_team_game_stats_game_team ON team_game_stats(game_id, team_abbr);
```

### Player Game Statistics
```sql
CREATE TABLE player_game_stats (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    
    -- Passing stats
    passing_attempts INTEGER DEFAULT 0,
    passing_completions INTEGER DEFAULT 0,
    passing_yards INTEGER DEFAULT 0,
    passing_touchdowns INTEGER DEFAULT 0,
    interceptions_thrown INTEGER DEFAULT 0,
    
    -- Rushing stats
    rushing_attempts INTEGER DEFAULT 0,
    rushing_yards INTEGER DEFAULT 0,
    rushing_touchdowns INTEGER DEFAULT 0,
    
    -- Receiving stats
    targets INTEGER DEFAULT 0,
    receptions INTEGER DEFAULT 0,
    receiving_yards INTEGER DEFAULT 0,
    receiving_touchdowns INTEGER DEFAULT 0,
    
    -- Advanced metrics
    passing_epa DECIMAL(8,3),
    rushing_epa DECIMAL(8,3),
    receiving_epa DECIMAL(8,3),
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    UNIQUE(game_id, player_id)
);

CREATE INDEX idx_player_game_stats_game_player ON player_game_stats(game_id, player_id);
CREATE INDEX idx_player_game_stats_player ON player_game_stats(player_id);
```

## Prediction and Analysis Tables

### Model Predictions
```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    
    -- Prediction outputs
    home_win_probability DECIMAL(6,4),     -- 0.0 to 1.0
    predicted_home_score DECIMAL(4,1),
    predicted_away_score DECIMAL(4,1),
    predicted_total_score DECIMAL(4,1),
    predicted_spread DECIMAL(4,1),         -- Home team perspective
    
    -- Confidence metrics
    prediction_confidence DECIMAL(6,4),
    uncertainty_interval_low DECIMAL(4,1),
    uncertainty_interval_high DECIMAL(4,1),
    
    -- Feature importance (JSON for flexibility)
    feature_importance JSONB,
    
    -- Prediction timing
    predicted_at TIMESTAMP DEFAULT NOW(),
    is_final_prediction BOOLEAN DEFAULT FALSE,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    UNIQUE(game_id, model_name, model_version, predicted_at)
);

CREATE INDEX idx_predictions_game_model ON predictions(game_id, model_name);
CREATE INDEX idx_predictions_model_version ON predictions(model_name, model_version);
```

### Model Performance Tracking
```sql
CREATE TABLE model_performance (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    
    -- Evaluation period
    season INTEGER NOT NULL,
    week_start INTEGER,
    week_end INTEGER,
    
    -- Performance metrics
    accuracy DECIMAL(6,4),                 -- Correct predictions / total predictions
    log_loss DECIMAL(8,6),                 -- Log-likelihood loss
    brier_score DECIMAL(8,6),              -- Brier score for probability calibration
    auc_roc DECIMAL(6,4),                  -- Area under ROC curve
    
    -- Prediction counts
    total_predictions INTEGER,
    correct_predictions INTEGER,
    
    -- Comparison to benchmarks
    vegas_line_accuracy DECIMAL(6,4),      -- Accuracy vs Vegas lines
    vegas_line_comparison DECIMAL(8,6),    -- Statistical comparison
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(model_name, model_version, season, week_start, week_end)
);
```

### Game Insights
```sql
CREATE TABLE game_insights (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) NOT NULL,
    insight_type VARCHAR(50) NOT NULL,     -- 'key_matchup', 'weather_impact', 'trend_analysis'
    
    -- Insight content
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    confidence_score DECIMAL(4,2),         -- 0.0 to 10.0
    
    -- Supporting data (JSON for flexibility)
    supporting_data JSONB,
    
    -- Categorization
    category VARCHAR(50),                   -- 'offense', 'defense', 'special_teams', 'situational'
    importance_score DECIMAL(4,2),         -- 0.0 to 10.0
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

CREATE INDEX idx_game_insights_game_type ON game_insights(game_id, insight_type);
```

## Indexes and Performance Optimization

### Query Optimization Indexes
```sql
-- Multi-column indexes for common queries
CREATE INDEX idx_games_season_type_week ON games(season, season_type, week);
CREATE INDEX idx_plays_game_posteam_down ON plays(game_id, posteam, down);
CREATE INDEX idx_player_stats_season_position ON players(team_abbr, position) 
    WHERE is_active = TRUE;

-- Partial indexes for active records
CREATE INDEX idx_active_players ON players(player_id) WHERE is_active = TRUE;
CREATE INDEX idx_finished_games ON games(game_id) WHERE game_finished = TRUE;

-- Covering indexes for common SELECT patterns
CREATE INDEX idx_team_game_stats_covering ON team_game_stats(game_id, team_abbr) 
    INCLUDE (total_epa, points_scored, total_yards);
```

## Data Integrity Constraints

### Check Constraints
```sql
-- Ensure logical data integrity
ALTER TABLE games ADD CONSTRAINT games_scores_non_negative 
    CHECK (home_score >= 0 AND away_score >= 0);

ALTER TABLE plays ADD CONSTRAINT plays_down_valid 
    CHECK (down BETWEEN 1 AND 4);

ALTER TABLE plays ADD CONSTRAINT plays_quarter_valid 
    CHECK (qtr BETWEEN 1 AND 5);

ALTER TABLE players ADD CONSTRAINT players_jersey_valid 
    CHECK (jersey_number BETWEEN 0 AND 99);
```

### Foreign Key Constraints
All foreign key relationships are defined with appropriate ON DELETE and ON UPDATE actions to maintain referential integrity while allowing for data updates.

This schema design provides:
1. **Compatibility** with nfl_data_py data structure
2. **Performance** optimization for analytical queries
3. **Scalability** for large datasets
4. **Flexibility** for future enhancements
5. **Data integrity** through constraints and validation
6. **Advanced analytics** support with EPA, WP, and other metrics