"""Web interface routes for NFL Analysis Engine."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text
from datetime import date, datetime, timedelta
from typing import Optional, List
import logging

from ..api.dependencies import get_db_session
from ..models.team import TeamModel
from ..models.game import GameModel
from ..models.player import PlayerModel
from ..models.play import PlayModel
from ..analysis.models import NFLPredictor
from ..analysis.vegas import VegasValidator
from ..analysis.insights import InsightsGenerator
from ..analysis.position_analytics import PositionAnalytics
from ..analysis.team_analytics import TeamAnalyticsCalculator
# from ..analysis.player_stats import PlayerStatsCalculator  # Temporarily disabled due to import issues
from ..api.routers.predictions import get_predictor

logger = logging.getLogger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="src/web/templates")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db_session)):
    """Home page with dashboard overview."""
    try:
        # Get basic stats with optimized query (single database round trip)
        stats = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM teams) as total_teams,
                (SELECT COUNT(*) FROM games) as total_games,
                (SELECT COUNT(*) FROM players) as total_players
        """)).first()
        
        total_teams = stats.total_teams
        total_games = stats.total_games
        total_players = stats.total_players
        
        # Get recent games
        recent_games = db.query(GameModel).filter(
            GameModel.home_score.isnot(None)
        ).order_by(GameModel.game_date.desc()).limit(5).all()
        
        # Get upcoming games
        upcoming_games = db.query(GameModel).filter(
            GameModel.home_score.is_(None),
            GameModel.game_date >= date.today()
        ).order_by(GameModel.game_date.asc()).limit(5).all()
        
        return templates.TemplateResponse("home.html", {
            "request": request,
            "total_teams": total_teams,
            "total_games": total_games,
            "total_players": total_players,
            "recent_games": recent_games,
            "upcoming_games": upcoming_games
        })
    except Exception as e:
        logger.error(f"Error loading home page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load dashboard data"
        })


@router.get("/teams", response_class=HTMLResponse)
async def teams_page(request: Request, db: Session = Depends(get_db_session)):
    """Teams listing page."""
    try:
        teams = db.query(TeamModel).order_by(TeamModel.team_conf, TeamModel.team_division, TeamModel.team_name).all()
        
        # Group teams by conference and division
        nfc_teams = [t for t in teams if t.team_conf == "NFC"]
        afc_teams = [t for t in teams if t.team_conf == "AFC"]
        
        return templates.TemplateResponse("teams.html", {
            "request": request,
            "nfc_teams": nfc_teams,
            "afc_teams": afc_teams
        })
    except Exception as e:
        logger.error(f"Error loading teams page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load teams data"
        })


@router.get("/team/{team_abbr}", response_class=HTMLResponse)
async def team_detail(request: Request, team_abbr: str, db: Session = Depends(get_db_session)):
    """Team detail page."""
    try:
        team = db.query(TeamModel).filter(TeamModel.team_abbr == team_abbr.upper()).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get team's recent games
        recent_games = db.query(GameModel).filter(
            (GameModel.home_team == team_abbr.upper()) | 
            (GameModel.away_team == team_abbr.upper())
        ).filter(
            GameModel.home_score.isnot(None)
        ).order_by(GameModel.game_date.desc()).limit(10).all()
        
        # Get team's upcoming games
        upcoming_games = db.query(GameModel).filter(
            (GameModel.home_team == team_abbr.upper()) | 
            (GameModel.away_team == team_abbr.upper())
        ).filter(
            GameModel.home_score.is_(None),
            GameModel.game_date >= date.today()
        ).order_by(GameModel.game_date.asc()).limit(5).all()
        
        # Calculate basic stats
        total_games = len(recent_games)
        wins = 0
        losses = 0
        
        for game in recent_games:
            if game.home_team == team_abbr.upper():
                if game.home_score > game.away_score:
                    wins += 1
                else:
                    losses += 1
            else:
                if game.away_score > game.home_score:
                    wins += 1
                else:
                    losses += 1
        
        win_percentage = (wins / total_games) if total_games > 0 else 0
        
        # Get team roster
        roster_players = db.query(PlayerModel).filter(
            PlayerModel.team_abbr == team_abbr.upper()
        ).order_by(PlayerModel.position.asc(), PlayerModel.jersey_number.asc()).all()
        
        # Group players by position group
        roster_by_position = {}
        if roster_players:
            for player in roster_players:
                if player.position:
                    # Map positions to position groups
                    position_groups = {
                        'QB': 'Offense', 'RB': 'Offense', 'FB': 'Offense', 'WR': 'Offense', 'TE': 'Offense',
                        'C': 'Offense', 'G': 'Offense', 'T': 'Offense', 'OL': 'Offense', 'OG': 'Offense', 'OT': 'Offense',
                        'DL': 'Defense', 'DE': 'Defense', 'DT': 'Defense', 'NT': 'Defense',
                        'LB': 'Defense', 'ILB': 'Defense', 'OLB': 'Defense', 'MLB': 'Defense',
                        'DB': 'Defense', 'CB': 'Defense', 'S': 'Defense', 'SS': 'Defense', 'FS': 'Defense',
                        'K': 'Special Teams', 'P': 'Special Teams', 'LS': 'Special Teams'
                    }
                    
                    group = position_groups.get(player.position, 'Other')
                    if group not in roster_by_position:
                        roster_by_position[group] = []
                    roster_by_position[group].append(player)
        
        return templates.TemplateResponse("team_detail.html", {
            "request": request,
            "team": team,
            "recent_games": recent_games,
            "upcoming_games": upcoming_games,
            "wins": wins,
            "losses": losses,
            "win_percentage": win_percentage,
            "roster_players": roster_players,
            "roster_by_position": roster_by_position if roster_by_position else None
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading team detail page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load team data"
        })


@router.get("/games", response_class=HTMLResponse)
async def games_page(
    request: Request, 
    week: Optional[int] = Query(None),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db_session)
):
    """Games listing page with optional filters."""
    try:
        # Default to 2024 since that's our most recent complete season data
        current_season = season or 2024
        
        # Build query
        query = db.query(GameModel).filter(GameModel.season == current_season)
        
        if week:
            query = query.filter(GameModel.week == week)
        
        games = query.order_by(GameModel.game_date.desc(), GameModel.game_id).limit(50).all()
        
        # Get available weeks for filter
        available_weeks = db.query(GameModel.week).filter(
            GameModel.season == current_season,
            GameModel.week.isnot(None)
        ).distinct().order_by(GameModel.week).all()
        available_weeks = [w[0] for w in available_weeks]
        
        return templates.TemplateResponse("games.html", {
            "request": request,
            "games": games,
            "current_week": week,
            "current_season": current_season,
            "available_weeks": available_weeks
        })
    except Exception as e:
        logger.error(f"Error loading games page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load games data"
        })


@router.get("/predictions", response_class=HTMLResponse)
async def predictions_page(request: Request, db: Session = Depends(get_db_session)):
    """Predictions page."""
    try:
        # Check if model is trained
        predictor = NFLPredictor(db)
        try:
            predictor.load_model()
            model_trained = True
        except FileNotFoundError:
            model_trained = False
        
        predictions = []
        if model_trained:
            # Get upcoming games for predictions
            upcoming_games = db.query(GameModel).filter(
                GameModel.home_score.is_(None),
                GameModel.game_date >= date.today(),
                GameModel.game_date <= date.today() + timedelta(days=14)
            ).order_by(GameModel.game_date.asc()).limit(10).all()
            
            # Generate predictions
            for game in upcoming_games:
                try:
                    prediction = predictor.predict_game(
                        home_team=game.home_team,
                        away_team=game.away_team,
                        game_date=game.game_date,
                        season=game.season
                    )
                    predictions.append({
                        'game': game,
                        'prediction': prediction
                    })
                except Exception as e:
                    logger.warning(f"Failed to predict {game.game_id}: {e}")
                    continue
        
        return templates.TemplateResponse("predictions.html", {
            "request": request,
            "model_trained": model_trained,
            "predictions": predictions
        })
    except Exception as e:
        logger.error(f"Error loading predictions page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load predictions data"
        })


@router.get("/predict", response_class=HTMLResponse)
async def predict_form(request: Request, db: Session = Depends(get_db_session)):
    """Manual prediction form."""
    try:
        # Get list of teams for dropdown
        teams = db.query(TeamModel).order_by(TeamModel.team_name).all()
        
        # Calculate default game date (7 days from now)
        from datetime import datetime, timedelta
        default_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        current_season = datetime.now().year
        
        return templates.TemplateResponse("predict_form.html", {
            "request": request,
            "teams": teams,
            "default_date": default_date,
            "current_season": current_season
        })
    except Exception as e:
        logger.error(f"Error loading predict form: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load prediction form"
        })


@router.post("/predict", response_class=HTMLResponse)
async def predict_game(
    request: Request,
    home_team: str = Form(...),
    away_team: str = Form(...),
    game_date: str = Form(...),
    season: Optional[int] = Form(None),
    db: Session = Depends(get_db_session)
):
    """Process manual prediction form."""
    try:
        # Parse game date
        game_date_obj = datetime.strptime(game_date, "%Y-%m-%d").date()
        season_year = season or game_date_obj.year
        
        # Get predictor
        predictor = NFLPredictor(db)
        try:
            predictor.load_model()
        except FileNotFoundError:
            return templates.TemplateResponse("predict_result.html", {
                "request": request,
                "error": "Model not trained. Please train the model first."
            })
        
        # Make prediction
        prediction = predictor.predict_game(
            home_team=home_team.upper(),
            away_team=away_team.upper(),
            game_date=game_date_obj,
            season=season_year
        )
        
        # Get team details
        home_team_obj = db.query(TeamModel).filter(TeamModel.team_abbr == home_team.upper()).first()
        away_team_obj = db.query(TeamModel).filter(TeamModel.team_abbr == away_team.upper()).first()
        
        return templates.TemplateResponse("predict_result.html", {
            "request": request,
            "prediction": prediction,
            "home_team_obj": home_team_obj,
            "away_team_obj": away_team_obj,
            "game_date": game_date_obj
        })
        
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        return templates.TemplateResponse("predict_result.html", {
            "request": request,
            "error": f"Failed to make prediction: {str(e)}"
        })


@router.get("/value-bets", response_class=HTMLResponse)
async def value_bets_page(request: Request, db: Session = Depends(get_db_session)):
    """Value betting opportunities page."""
    try:
        # Check if model is trained
        predictor = NFLPredictor(db)
        try:
            predictor.load_model()
            model_trained = True
        except FileNotFoundError:
            model_trained = False
        
        value_bets = []
        if model_trained:
            # Get value bets
            validator = VegasValidator(db, predictor)
            try:
                value_bets = validator.get_upcoming_value_bets(weeks_ahead=2, min_edge=0.05)
            except Exception as e:
                logger.warning(f"Failed to get value bets: {e}")
        
        return templates.TemplateResponse("value_bets.html", {
            "request": request,
            "model_trained": model_trained,
            "value_bets": value_bets
        })
    except Exception as e:
        logger.error(f"Error loading value bets page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load value bets data"
        })


@router.get("/model", response_class=HTMLResponse)
async def model_status_page(request: Request, db: Session = Depends(get_db_session)):
    """Model status and training page."""
    try:
        predictor = NFLPredictor(db)
        
        # Check model status
        model_trained = False
        training_metrics = None
        validation_metrics = None
        feature_importance = {}
        
        try:
            predictor.load_model()
            model_trained = True
            training_metrics = predictor.training_metrics
            validation_metrics = predictor.validation_metrics
            
            # Get top features
            try:
                feature_importance = predictor.get_feature_importance(top_n=10)
            except Exception as e:
                logger.warning(f"Could not get feature importance: {e}")
        except FileNotFoundError:
            model_trained = False
        
        # Get available seasons for training
        available_seasons = db.query(GameModel.season).distinct().order_by(GameModel.season.desc()).all()
        available_seasons = [s[0] for s in available_seasons if s[0]]
        
        return templates.TemplateResponse("model_status.html", {
            "request": request,
            "model_trained": model_trained,
            "training_metrics": training_metrics,
            "validation_metrics": validation_metrics,
            "feature_importance": feature_importance,
            "available_seasons": available_seasons
        })
    except Exception as e:
        logger.error(f"Error loading model status page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load model status"
        })


@router.post("/train-model", response_class=HTMLResponse)
async def train_model(
    request: Request,
    seasons: str = Form(...),
    test_size: float = Form(0.2),
    db: Session = Depends(get_db_session)
):
    """Train the prediction model."""
    try:
        # Parse seasons
        season_list = [int(s.strip()) for s in seasons.split(",") if s.strip().isdigit()]
        
        if not season_list:
            raise ValueError("No valid seasons provided")
        
        # Train model
        predictor = NFLPredictor(db)
        predictor.train(
            seasons=season_list,
            test_size=test_size,
            optimize_hyperparameters=False  # Keep it fast for web UI
        )
        
        # Save model
        predictor.save_model()
        
        return templates.TemplateResponse("train_result.html", {
            "request": request,
            "success": True,
            "message": f"Model trained successfully on seasons: {', '.join(map(str, season_list))}",
            "training_metrics": predictor.training_metrics,
            "validation_metrics": predictor.validation_metrics
        })
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return templates.TemplateResponse("train_result.html", {
            "request": request,
            "success": False,
            "error": f"Failed to train model: {str(e)}"
        })


@router.get("/players", response_class=HTMLResponse)
async def players_page(
    request: Request, 
    team: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session)
):
    """Enhanced players directory page."""
    try:
        # Get total player count
        total_players = db.query(PlayerModel).count()
        
        # Get teams for navigation
        teams = db.query(TeamModel).order_by(TeamModel.team_name).all()
        
        # Build player query with filters
        query = db.query(PlayerModel)
        
        if team:
            query = query.filter(PlayerModel.team_abbr == team.upper())
        
        if position:
            query = query.filter(PlayerModel.position == position.upper())
        
        # Get players with pagination
        players = query.order_by(
            PlayerModel.team_abbr.asc(),
            PlayerModel.position.asc(), 
            PlayerModel.full_name.asc()
        ).offset(offset).limit(limit).all()
        
        # Calculate position data coverage
        players_with_position = db.query(PlayerModel).filter(
            PlayerModel.position.isnot(None)
        ).count()
        
        position_coverage_percent = round((players_with_position / max(total_players, 1)) * 100, 1)
        show_position_warning = position_coverage_percent < 50
        
        return templates.TemplateResponse("players_new.html", {
            "request": request,
            "players": players,
            "teams": teams,
            "total_players": total_players,
            "position_coverage_percent": position_coverage_percent,
            "show_position_warning": show_position_warning,
            "current_team": team,
            "current_position": position
        })
        
    except Exception as e:
        logger.error(f"Error loading players page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load players page"
        })


@router.get("/player/{player_id}", response_class=HTMLResponse)
async def player_detail_page(request: Request, player_id: str, db: Session = Depends(get_db_session)):
    """Individual player profile page."""
    try:
        # Get player info
        player = db.query(PlayerModel).filter(PlayerModel.player_id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Get team info if player has team
        team = None
        if player.team_abbr:
            team = db.query(TeamModel).filter(TeamModel.team_abbr == player.team_abbr).first()
        
        # Get recent games for this player's team
        recent_games = []
        if player.team_abbr:
            recent_games = db.query(GameModel).filter(
                (GameModel.home_team == player.team_abbr) | 
                (GameModel.away_team == player.team_abbr)
            ).filter(
                GameModel.home_score.isnot(None)
            ).order_by(GameModel.game_date.desc()).limit(10).all()
        
        # Get player statistics (placeholder for now)
        player_stats = []
        # In the future, this would aggregate play-by-play stats for the player
        
        # Get similar players (placeholder for now)
        similar_players = []
        if player.position:
            similar_players = db.query(PlayerModel).filter(
                PlayerModel.position == player.position,
                PlayerModel.team_abbr == player.team_abbr,
                PlayerModel.player_id != player.player_id
            ).limit(3).all()
        
        # Generate career events
        career_events = []
        if player.rookie_year:
            career_events.append({
                'year': player.rookie_year,
                'description': f'Entered NFL as rookie'
            })
        if player.draft_year and player.draft_round and player.draft_pick:
            career_events.append({
                'year': player.draft_year,
                'description': f'Drafted in Round {player.draft_round}, Pick {player.draft_pick}'
            })
        
        return templates.TemplateResponse("player_detail.html", {
            "request": request,
            "player": player,
            "team": team,
            "recent_games": recent_games,
            "player_stats": player_stats,
            "similar_players": similar_players,
            "career_events": career_events if career_events else None
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading player detail: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load player details"
        })


@router.get("/schedule", response_class=HTMLResponse)
async def schedule_page(
    request: Request, 
    week: Optional[int] = Query(None),
    season: Optional[int] = Query(None),
    db: Session = Depends(get_db_session)
):
    """Enhanced schedule and upcoming games page."""
    try:
        # Default to 2024 season
        current_season = season or 2024
        
        # Get available weeks
        available_weeks = db.query(GameModel.week).filter(
            GameModel.season == current_season,
            GameModel.week.isnot(None)
        ).distinct().order_by(GameModel.week).all()
        available_weeks = [w[0] for w in available_weeks]
        
        # Determine current week (default to next upcoming week)
        if not week:
            # Find the first week with upcoming games
            upcoming_week = db.query(GameModel.week).filter(
                GameModel.season == current_season,
                GameModel.home_score.is_(None),
                GameModel.game_date >= date.today(),
                GameModel.week.isnot(None)
            ).order_by(GameModel.week.asc()).first()
            
            current_week = upcoming_week[0] if upcoming_week else (available_weeks[0] if available_weeks else 1)
        else:
            current_week = week
        
        # Get games for the selected week
        games_query = db.query(GameModel).filter(GameModel.season == current_season)
        
        if current_week:
            games_query = games_query.filter(GameModel.week == current_week)
        
        upcoming_games = games_query.order_by(
            GameModel.game_date.asc(), 
            GameModel.game_id.asc()
        ).all()
        
        # Get current month/year for calendar
        from datetime import datetime
        now = datetime.now()
        current_month = now.month - 1  # JavaScript months are 0-indexed
        current_year = now.year
        current_month_year = now.strftime("%B %Y")
        
        return templates.TemplateResponse("schedule.html", {
            "request": request,
            "upcoming_games": upcoming_games,
            "current_week": current_week,
            "available_weeks": available_weeks,
            "current_season": current_season,
            "current_month": current_month,
            "current_year": current_year,
            "current_month_year": current_month_year
        })
        
    except Exception as e:
        logger.error(f"Error loading schedule page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load schedule data"
        })


@router.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request, db: Session = Depends(get_db_session)):
    """Insights dashboard page."""
    try:
        # Get list of teams for dropdown
        teams = db.query(TeamModel).order_by(TeamModel.team_name).all()
        
        # Get available seasons
        available_seasons = db.query(GameModel.season).distinct().order_by(GameModel.season.desc()).all()
        available_seasons = [s[0] for s in available_seasons if s[0]]
        
        return templates.TemplateResponse("insights.html", {
            "request": request,
            "teams": teams,
            "available_seasons": available_seasons
        })
    except Exception as e:
        logger.error(f"Error loading insights page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load insights page"
        })


@router.get("/insights/team/{team_abbr}/{season}", response_class=HTMLResponse)
async def team_insights_page(
    request: Request, 
    team_abbr: str, 
    season: int, 
    db: Session = Depends(get_db_session)
):
    """Team insights detail page."""
    try:
        # Get team info
        team = db.query(TeamModel).filter(TeamModel.team_abbr == team_abbr.upper()).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Generate insights
        generator = InsightsGenerator(db)
        insights = generator.generate_team_insights(team_abbr.upper(), season)
        
        if not insights:
            return templates.TemplateResponse("team_insights.html", {
                "request": request,
                "team": team,
                "season": season,
                "insights": None,
                "error": "No insights available for this team and season"
            })
        
        # Generate season narrative
        narrative = generator.generate_season_narrative(team_abbr.upper(), season)
        
        return templates.TemplateResponse("team_insights.html", {
            "request": request,
            "team": team,
            "season": season,
            "insights": insights,
            "narrative": narrative
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading team insights: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load team insights"
        })


@router.get("/insights/compare", response_class=HTMLResponse)
async def team_comparison_form(request: Request, db: Session = Depends(get_db_session)):
    """Team comparison form."""
    try:
        # Get list of teams for dropdown
        teams = db.query(TeamModel).order_by(TeamModel.team_name).all()
        
        # Get available seasons
        available_seasons = db.query(GameModel.season).distinct().order_by(GameModel.season.desc()).all()
        available_seasons = [s[0] for s in available_seasons if s[0]]
        
        return templates.TemplateResponse("team_comparison_form.html", {
            "request": request,
            "teams": teams,
            "available_seasons": available_seasons
        })
    except Exception as e:
        logger.error(f"Error loading comparison form: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load comparison form"
        })


@router.post("/insights/compare", response_class=HTMLResponse)
async def team_comparison_result(
    request: Request,
    team1: str = Form(...),
    team2: str = Form(...),
    season: int = Form(...),
    db: Session = Depends(get_db_session)
):
    """Team comparison results."""
    try:
        # Get team info
        team1_obj = db.query(TeamModel).filter(TeamModel.team_abbr == team1.upper()).first()
        team2_obj = db.query(TeamModel).filter(TeamModel.team_abbr == team2.upper()).first()
        
        if not team1_obj or not team2_obj:
            raise HTTPException(status_code=404, detail="One or both teams not found")
        
        # Generate comparison
        generator = InsightsGenerator(db)
        comparison = generator.compare_teams(team1.upper(), team2.upper(), season)
        
        if not comparison:
            return templates.TemplateResponse("team_comparison_result.html", {
                "request": request,
                "team1_obj": team1_obj,
                "team2_obj": team2_obj,
                "season": season,
                "comparison": None,
                "error": "Unable to compare teams for this season"
            })
        
        return templates.TemplateResponse("team_comparison_result.html", {
            "request": request,
            "team1_obj": team1_obj,
            "team2_obj": team2_obj,
            "season": season,
            "comparison": comparison
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing teams: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to compare teams"
        })


@router.get("/league-leaders", response_class=HTMLResponse)
async def league_leaders_page(
    request: Request,
    season: Optional[int] = Query(None),
    category: Optional[str] = Query("all"),
    db: Session = Depends(get_db_session)
):
    """Comprehensive league leaders page with real NFL data from PostgreSQL."""
    try:
        # Default to current season
        if not season:
            # Get the most recent season with data
            latest_season = db.query(func.max(PlayModel.season)).scalar()
            season = latest_season or 2024
        
        # Use enhanced position analytics
        analytics = PositionAnalytics(db)
        position_data = analytics.get_position_leaders(season, 'all')
        
        # Convert dataclass objects to dictionaries for template
        qb_stats = position_data.get('quarterbacks', [])
        rb_stats = position_data.get('running_backs', [])
        wr_stats = position_data.get('receivers', [])
        
        # Build leaders data
        leaders_data = {
            'quarterbacks': qb_stats,
            'running_backs': rb_stats,
            'receivers': wr_stats,
            'team_offense': [],
            'season': season
        }
        
        # Get available seasons for dropdown
        available_seasons = db.query(PlayModel.season).distinct().order_by(PlayModel.season.desc()).all()
        available_seasons = [s[0] for s in available_seasons if s[0]]
        
        return templates.TemplateResponse("league_leaders.html", {
            "request": request,
            "leaders": leaders_data,
            "season": season,
            "category": category,
            "available_seasons": available_seasons,
            "thresholds": {
                "qb_attempts": 150,
                "rb_carries": 75,
                "wr_targets": 30  
            }
        })
        
    except Exception as e:
        logger.error(f"Error loading league leaders: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to load league leaders: {str(e)}"
        })


@router.get("/league-leaders-nfl", response_class=HTMLResponse)
async def league_leaders_nfl_page(
    request: Request,
    season: Optional[int] = Query(None),
    category: Optional[str] = Query("all")
):
    """League leaders page with real NFL data from SQLite database."""
    try:
        # Import SQLite support
        import sqlite3
        import os
        
        # Default to 2024 season (the season we have data for)
        if not season:
            season = 2024
        
        # Connect directly to SQLite database
        db_path = os.path.join(os.getcwd(), "nfl_data.db")
        if not os.path.exists(db_path):
            raise Exception("NFL data database not found. Please run the data setup script.")
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        # Get QB stats with NFL passer rating formula
        qb_stats = []
        cursor.execute("""
            SELECT 
                passer_player_name,
                posteam,
                COUNT(*) as attempts,
                SUM(passing_yards) as total_yards,
                AVG(passing_yards) as avg_per_attempt,
                SUM(CASE WHEN pass_touchdown > 0 THEN 1 ELSE 0 END) as touchdowns,
                SUM(CASE WHEN interception > 0 THEN 1 ELSE 0 END) as interceptions,
                SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END) as completions,
                AVG(epa) as avg_epa
            FROM plays 
            WHERE pass_attempt = 1.0 
 
                AND passer_player_name IS NOT NULL
                AND season = ?
            GROUP BY passer_player_name, posteam 
            HAVING attempts >= 150
            ORDER BY total_yards DESC 
            LIMIT 15
        """, (season,))
        
        qb_results = cursor.fetchall()
        for row in qb_results:
            attempts = row['attempts'] or 1
            completions = row['completions'] or 0
            yards = row['total_yards'] or 0
            tds = row['touchdowns'] or 0
            ints = row['interceptions'] or 0
            
            # Calculate NFL passer rating
            comp_pct = (completions / attempts) * 100 if attempts > 0 else 0
            ypa = yards / attempts if attempts > 0 else 0
            td_pct = (tds / attempts) * 100 if attempts > 0 else 0
            int_pct = (ints / attempts) * 100 if attempts > 0 else 0
            
            # NFL passer rating formula components
            a = max(0, min(2.375, ((comp_pct - 30) * 0.05)))
            b = max(0, min(2.375, ((ypa - 3) * 0.25)))
            c = max(0, min(2.375, (td_pct * 0.2)))
            d = max(0, min(2.375, (2.375 - (int_pct * 0.25))))
            
            passer_rating = ((a + b + c + d) / 6) * 100
            
            qb_stats.append({
                'player_name': row['passer_player_name'],
                'team': row['posteam'],
                'attempts': attempts,
                'completion_pct': round(comp_pct, 1),
                'passing_yards': int(yards),
                'passing_tds': tds,
                'interceptions': ints,
                'passer_rating': round(passer_rating, 1),
                'yards_per_attempt': round(ypa, 1),
                'avg_epa': round(row['avg_epa'] or 0, 3)
            })
        
        # Get RB stats with meaningful thresholds
        rb_stats = []
        cursor.execute("""
            SELECT 
                rusher_player_name,
                posteam,
                COUNT(*) as carries,
                SUM(rushing_yards) as total_yards,
                AVG(rushing_yards) as avg_per_carry,
                SUM(CASE WHEN rush_touchdown > 0 THEN 1 ELSE 0 END) as touchdowns,
                MAX(rushing_yards) as longest,
                AVG(epa) as avg_epa
            FROM plays 
            WHERE rush_attempt = 1.0 
 
                AND rusher_player_name IS NOT NULL
                AND season = ?
            GROUP BY rusher_player_name, posteam 
            HAVING carries >= 75
            ORDER BY total_yards DESC 
            LIMIT 15
        """, (season,))
        
        rb_results = cursor.fetchall()
        for row in rb_results:
            rb_stats.append({
                'player_name': row['rusher_player_name'],
                'team': row['posteam'],
                'carries': row['carries'] or 0,
                'rushing_yards': int(row['total_yards'] or 0),
                'rushing_tds': row['touchdowns'] or 0,
                'yards_per_carry': round(row['avg_per_carry'] or 0, 1),
                'longest_run': row['longest'] or 0,
                'avg_epa': round(row['avg_epa'] or 0, 3)
            })
        
        # Get WR stats
        wr_stats = []
        cursor.execute("""
            SELECT 
                receiver_player_name,
                posteam,
                COUNT(*) as catches,
                SUM(receiving_yards) as total_yards,
                AVG(receiving_yards) as avg_per_catch,
                SUM(CASE WHEN pass_touchdown > 0 THEN 1 ELSE 0 END) as touchdowns,
                AVG(epa) as avg_epa
            FROM plays 
            WHERE complete_pass = 1
 
                AND receiver_player_name IS NOT NULL
                AND season = ?
            GROUP BY receiver_player_name, posteam 
            HAVING catches >= 30
            ORDER BY total_yards DESC 
            LIMIT 15
        """, (season,))
        
        wr_results = cursor.fetchall()
        for row in wr_results:
            wr_stats.append({
                'player_name': row['receiver_player_name'],
                'team': row['posteam'],
                'catches': row['catches'] or 0,
                'receiving_yards': int(row['total_yards'] or 0),
                'receiving_tds': row['touchdowns'] or 0,
                'yards_per_catch': round(row['avg_per_catch'] or 0, 1),
                'avg_epa': round(row['avg_epa'] or 0, 3),
                'targets': row['catches'] or 0  # Placeholder - catches is close to targets
            })
        
        conn.close()
        
        # Build leaders data
        leaders_data = {
            'quarterbacks': qb_stats,
            'running_backs': rb_stats,
            'receivers': wr_stats,
            'team_offense': [],
            'season': season
        }
        
        return templates.TemplateResponse("league_leaders.html", {
            "request": request,
            "leaders": leaders_data,
            "season": season,
            "available_seasons": [2024],  # Only 2024 data available
            "category": category,
            "thresholds": {
                "qb_attempts": 150,
                "rb_carries": 75,
                "wr_targets": 30  
            }
        })
        
    except Exception as e:
        logger.error(f"Error loading NFL league leaders: {e}")
        import traceback
        traceback.print_exc()
        
        # Return error template
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to load NFL league leaders: {str(e)}"
        })


@router.get("/insights/leaders/{season}", response_class=HTMLResponse)
async def old_league_leaders_page(
    request: Request, 
    season: int,
    metric: str = Query("offensive_epa_per_play", description="Metric to rank by"),
    db: Session = Depends(get_db_session)
):
    """Legacy league leaders page - redirects to new page."""
    # Redirect to new league leaders page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/web/league-leaders?season={season}", status_code=302)


@router.get("/game/{game_id}", response_class=HTMLResponse)
async def game_detail_page(request: Request, game_id: str, db: Session = Depends(get_db_session)):
    """Game detail page showing comprehensive stats."""
    try:
        # Get game info
        game = db.query(GameModel).filter(GameModel.game_id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Get team info
        home_team = db.query(TeamModel).filter(TeamModel.team_abbr == game.home_team).first()
        away_team = db.query(TeamModel).filter(TeamModel.team_abbr == game.away_team).first()
        
        # Calculate basic game stats
        game_stats = {
            'total_points': (game.home_score or 0) + (game.away_score or 0) if game.home_score is not None and game.away_score is not None else None,
            'point_differential': abs((game.home_score or 0) - (game.away_score or 0)) if game.home_score is not None and game.away_score is not None else None,
            'winner': game.home_team if (game.home_score or 0) > (game.away_score or 0) else game.away_team if game.home_score is not None and game.away_score is not None else None,
            'is_overtime': game.home_score is not None and game.away_score is not None and ((game.home_score or 0) + (game.away_score or 0)) > 40,  # Simple OT heuristic
        }
        
        # Get recent games between these teams
        head_to_head = db.query(GameModel).filter(
            ((GameModel.home_team == game.home_team) & (GameModel.away_team == game.away_team)) |
            ((GameModel.home_team == game.away_team) & (GameModel.away_team == game.home_team))
        ).filter(
            GameModel.game_date < game.game_date,
            GameModel.home_score.isnot(None)
        ).order_by(GameModel.game_date.desc()).limit(5).all()
        
        return templates.TemplateResponse("game_detail.html", {
            "request": request,
            "game": game,
            "home_team": home_team,
            "away_team": away_team,
            "game_stats": game_stats,
            "head_to_head": head_to_head
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading game detail: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load game details"
        })


@router.get("/team-analytics", response_class=HTMLResponse)
async def team_analytics_page(
    request: Request,
    season: Optional[int] = Query(None),
    category: Optional[str] = Query("overview"),
    db: Session = Depends(get_db_session)
):
    """Advanced team analytics page with comprehensive team performance metrics."""
    try:
        # Default to current season
        if not season:
            latest_season = db.query(func.max(PlayModel.season)).scalar()
            season = latest_season or 2024
        
        # Calculate team analytics
        analytics_calc = TeamAnalyticsCalculator(db)
        team_analytics = analytics_calc.calculate_team_analytics(season)
        
        # Get team rankings
        rankings = analytics_calc.get_team_rankings(season)
        
        # Get available seasons
        available_seasons = db.query(PlayModel.season).distinct().order_by(PlayModel.season.desc()).all()
        available_seasons = [s[0] for s in available_seasons if s[0]]
        
        return templates.TemplateResponse("team_analytics.html", {
            "request": request,
            "team_analytics": team_analytics,
            "rankings": rankings,
            "season": season,
            "category": category,
            "available_seasons": available_seasons
        })
        
    except Exception as e:
        logger.error(f"Error loading team analytics: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to load team analytics: {str(e)}"
        })


@router.get("/automation", response_class=HTMLResponse)
async def automation_page(request: Request, db: Session = Depends(get_db_session)):
    """Automation and data refresh management page."""
    try:
        from datetime import datetime
        from ..services.scheduler import get_global_scheduler
        
        # Get scheduler status
        scheduler = get_global_scheduler()
        scheduler_status = scheduler.get_status()
        
        # Get data status
        total_teams = db.query(TeamModel).count()
        total_games = db.query(GameModel).count()
        total_players = db.query(PlayerModel).count()
        
        return templates.TemplateResponse("automation.html", {
            "request": request,
            "scheduler_status": scheduler_status,
            "data_counts": {
                "teams": total_teams,
                "games": total_games,
                "players": total_players
            },
            "current_time": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error loading automation page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load automation page"
        })


@router.post("/automation/refresh", response_class=HTMLResponse)
async def trigger_data_refresh(request: Request, current_season_only: bool = Form(True)):
    """Trigger manual data refresh."""
    try:
        from ..services.scheduler import get_global_scheduler
        
        scheduler = get_global_scheduler()
        result = scheduler.trigger_immediate_refresh(current_season_only)
        
        return templates.TemplateResponse("refresh_result.html", {
            "request": request,
            "result": result,
            "success": result.get("status") == "success"
        })
    except Exception as e:
        logger.error(f"Error triggering data refresh: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Failed to trigger data refresh: {str(e)}"
        })


@router.get("/insights/game/{game_id}", response_class=HTMLResponse)
async def game_insights_page(request: Request, game_id: str, db: Session = Depends(get_db_session)):
    """Game insights detail page."""
    try:
        # Get game info
        game = db.query(GameModel).filter(GameModel.game_id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Generate insights
        generator = InsightsGenerator(db)
        insights = generator.generate_game_insights(game_id)
        
        if not insights:
            return templates.TemplateResponse("game_insights.html", {
                "request": request,
                "game": game,
                "insights": None,
                "error": "No insights available for this game"
            })
        
        return templates.TemplateResponse("game_insights.html", {
            "request": request,
            "game": game,
            "insights": insights
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading game insights: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load game insights"
        })