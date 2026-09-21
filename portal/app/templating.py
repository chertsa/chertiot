from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.features import feature_globals
from app.i18n import template_globals

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates"),
    context_processors=[template_globals, feature_globals],
)
