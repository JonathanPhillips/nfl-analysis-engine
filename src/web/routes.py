"""Web interface routes for NFL Analysis Engine."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional, List
import logging

from ..api.dependencies import get_db_session
from ..models.team import TeamModel
from ..models.game import GameModel
from ..models.player import PlayerModel
from ..analysis.models import NFLPredictor
from ..analysis.vegas import VegasValidator
from ..analysis.insights import InsightsGenerator
from ..api.routers.predictions import get_predictor

logger = logging.getLogger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="src/web/templates")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db_session)):
    """Home page with dashboard overview."""
    try:
        # Get basic stats
        total_teams = db.query(TeamModel).count()
        total_games = db.query(GameModel).count()
        total_players = db.query(PlayerModel).count()
        
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
        
        return templates.TemplateResponse("team_detail.html", {
            "request": request,
            "team": team,
            "recent_games": recent_games,
            "upcoming_games": upcoming_games,
            "wins": wins,
            "losses": losses,
            "win_percentage": win_percentage
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
        current_season = season or datetime.now().year
        
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
        
        return templates.TemplateResponse("predict_form.html", {
            "request": request,
            "teams": teams
        })
    except Exception as e:
        logger.error(f"Error loading predict form: {e}")
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
            optimize_hyperparameters=False,  # Keep it fast for web UI
            min_games_played=1
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


@router.get("/insights/leaders/{season}", response_class=HTMLResponse)
async def league_leaders_page(
    request: Request, 
    season: int,
    metric: str = Query("offensive_epa_per_play", description="Metric to rank by"),
    db: Session = Depends(get_db_session)
):
    """League leaders page."""
    try:
        # Generate league leaders
        generator = InsightsGenerator(db)
        leaders = generator.get_league_leaders(season, metric, limit=15)
        
        # Available metrics for dropdown
        available_metrics = [
            ("offensive_epa_per_play", "Offensive EPA per Play"),
            ("passing_epa_per_play", "Passing EPA per Play"),
            ("rushing_epa_per_play", "Rushing EPA per Play"),
            ("defensive_epa_per_play", "Defensive EPA per Play"),
            ("red_zone_efficiency", "Red Zone Efficiency"),
            ("third_down_conversion_rate", "3rd Down Conversion Rate"),
            ("clutch_performance", "Clutch Performance"),
            ("turnover_margin", "Turnover Margin")
        ]
        
        return templates.TemplateResponse("league_leaders.html", {
            "request": request,
            "season": season,
            "metric": metric,
            "leaders": leaders,
            "available_metrics": available_metrics
        })
    except Exception as e:
        logger.error(f"Error loading league leaders: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load league leaders"
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