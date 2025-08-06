"""API endpoints for NFL insights and advanced analytics."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from .dependencies import get_db_session
from ..analysis.insights import InsightsGenerator
from ..models.schemas import (
    AdvancedMetricsResponse,
    TeamInsightsResponse,
    GameInsightResponse,
    LeagueLeadersResponse,
    TeamComparisonResponse,
    SeasonNarrativeResponse
)

router = APIRouter(prefix="/insights", tags=["insights"])


def get_insights_generator(db: Session = Depends(get_db_session)) -> InsightsGenerator:
    """Get insights generator instance."""
    return InsightsGenerator(db)


@router.post("/play-metrics", response_model=AdvancedMetricsResponse)
def calculate_play_metrics(
    play_data: Dict[str, Any],
    generator: InsightsGenerator = Depends(get_insights_generator)
):
    """Calculate advanced metrics for a single play.
    
    Args:
        play_data: Play data dictionary with required fields:
            - down: Current down (1-4)
            - ydstogo: Yards to go for first down
            - yardline_100: Distance to goal line
            - qtr: Quarter (1-4)
            - game_seconds_remaining: Seconds left in game
            - score_differential: Point differential (positive if offense leading)
            - timeouts_remaining: Timeouts remaining
            - play_type: Type of play ('pass', 'run', etc.)
            - yards_gained: Yards gained on play
            - touchdown: Whether play resulted in touchdown
            - interception: Whether play resulted in interception
            - fumble_lost: Whether play resulted in lost fumble
    
    Returns:
        AdvancedMetrics with EPA, WPA, and other metrics
    """
    try:
        metrics = generator.calculate_play_metrics(play_data)
        return AdvancedMetricsResponse(
            status="success",
            message="Play metrics calculated successfully",
            data=metrics.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calculating play metrics: {str(e)}")


@router.get("/team/{team_abbr}/{season}", response_model=TeamInsightsResponse)
def get_team_insights(
    team_abbr: str,
    season: int,
    generator: InsightsGenerator = Depends(get_insights_generator)
):
    """Get comprehensive insights for a team in a specific season.
    
    Args:
        team_abbr: Team abbreviation (e.g., 'SF', 'KC')
        season: Season year
    
    Returns:
        TeamInsights with advanced metrics and analysis
    """
    try:
        insights = generator.generate_team_insights(team_abbr.upper(), season)
        if not insights:
            raise HTTPException(
                status_code=404, 
                detail=f"No insights found for {team_abbr} in {season}"
            )
        
        return TeamInsightsResponse(
            status="success",
            message=f"Team insights generated for {team_abbr} - {season}",
            data=insights.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating team insights: {str(e)}")


@router.get("/game/{game_id}", response_model=GameInsightResponse)
def get_game_insights(
    game_id: str,
    generator: InsightsGenerator = Depends(get_insights_generator)
):
    """Get insights for a specific game.
    
    Args:
        game_id: Game identifier
    
    Returns:
        GameInsight with game analysis
    """
    try:
        insights = generator.generate_game_insights(game_id)
        if not insights:
            raise HTTPException(
                status_code=404, 
                detail=f"No insights found for game {game_id}"
            )
        
        return GameInsightResponse(
            status="success",
            message=f"Game insights generated for {game_id}",
            data=insights.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating game insights: {str(e)}")


@router.get("/league-leaders/{season}", response_model=LeagueLeadersResponse)
def get_league_leaders(
    season: int,
    metric: str = Query(..., description="Metric name (e.g., 'offensive_epa_per_play')"),
    limit: int = Query(10, ge=1, le=32, description="Number of teams to return"),
    generator: InsightsGenerator = Depends(get_insights_generator)
):
    """Get league leaders for a specific advanced metric.
    
    Args:
        season: Season year
        metric: Metric name to rank by
        limit: Number of teams to return (1-32)
    
    Returns:
        List of team rankings with metric values
    """
    try:
        leaders = generator.get_league_leaders(season, metric, limit)
        return LeagueLeadersResponse(
            status="success",
            message=f"League leaders for {metric} in {season}",
            data={
                "season": season,
                "metric": metric,
                "leaders": leaders
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting league leaders: {str(e)}")


@router.get("/compare/{team1}/{team2}/{season}", response_model=TeamComparisonResponse)
def compare_teams(
    team1: str,
    team2: str,
    season: int,
    generator: InsightsGenerator = Depends(get_insights_generator)
):
    """Compare two teams using advanced metrics.
    
    Args:
        team1: First team abbreviation
        team2: Second team abbreviation  
        season: Season year
    
    Returns:
        Detailed comparison with advantages and metrics
    """
    try:
        comparison = generator.compare_teams(team1.upper(), team2.upper(), season)
        if not comparison:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to compare {team1} vs {team2} in {season}"
            )
        
        return TeamComparisonResponse(
            status="success",
            message=f"Team comparison: {team1} vs {team2} ({season})",
            data=comparison
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing teams: {str(e)}")


@router.get("/narrative/{team_abbr}/{season}", response_model=SeasonNarrativeResponse)
def get_season_narrative(
    team_abbr: str,
    season: int,
    generator: InsightsGenerator = Depends(get_insights_generator)
):
    """Generate a narrative summary of a team's season.
    
    Args:
        team_abbr: Team abbreviation
        season: Season year
    
    Returns:
        Narrative description of the team's season
    """
    try:
        narrative = generator.generate_season_narrative(team_abbr.upper(), season)
        return SeasonNarrativeResponse(
            status="success",
            message=f"Season narrative for {team_abbr} - {season}",
            data={
                "team": team_abbr.upper(),
                "season": season,
                "narrative": narrative
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating narrative: {str(e)}")


@router.get("/available-metrics")
def get_available_metrics():
    """Get list of available metrics for league leaders and comparisons.
    
    Returns:
        Dictionary with metric categories and descriptions
    """
    return {
        "status": "success",
        "message": "Available metrics for insights analysis",
        "data": {
            "offensive_metrics": [
                {
                    "name": "offensive_epa_per_play",
                    "description": "Expected Points Added per offensive play"
                },
                {
                    "name": "passing_epa_per_play", 
                    "description": "Expected Points Added per passing play"
                },
                {
                    "name": "rushing_epa_per_play",
                    "description": "Expected Points Added per rushing play"
                },
                {
                    "name": "red_zone_efficiency",
                    "description": "Percentage of red zone drives resulting in touchdowns"
                },
                {
                    "name": "third_down_conversion_rate",
                    "description": "Third down conversion percentage"
                }
            ],
            "defensive_metrics": [
                {
                    "name": "defensive_epa_per_play",
                    "description": "Expected Points Added allowed per defensive play (lower is better)"
                },
                {
                    "name": "pass_defense_epa",
                    "description": "Expected Points Added allowed on passing plays"
                },
                {
                    "name": "run_defense_epa", 
                    "description": "Expected Points Added allowed on rushing plays"
                },
                {
                    "name": "red_zone_defense",
                    "description": "Defensive red zone efficiency (lower is better)"
                },
                {
                    "name": "third_down_defense",
                    "description": "Third down conversion rate allowed (lower is better)"
                }
            ],
            "situational_metrics": [
                {
                    "name": "two_minute_drill_efficiency",
                    "description": "Performance in two-minute drill situations"
                },
                {
                    "name": "clutch_performance",
                    "description": "Performance in high-leverage situations"
                },
                {
                    "name": "turnover_margin",
                    "description": "Average turnover differential per game"
                }
            ],
            "contextual_metrics": [
                {
                    "name": "garbage_time_adjusted_epa",
                    "description": "EPA adjusted for garbage time scenarios"
                },
                {
                    "name": "strength_of_schedule",
                    "description": "Average opponent strength faced"
                },
                {
                    "name": "home_field_advantage",
                    "description": "Home vs away performance differential"
                }
            ],
            "trend_metrics": [
                {
                    "name": "early_season_performance",
                    "description": "Performance in first half of season"
                },
                {
                    "name": "late_season_performance", 
                    "description": "Performance in second half of season"
                },
                {
                    "name": "improvement_trajectory",
                    "description": "Rate of improvement throughout season"
                }
            ]
        }
    }