from mangum import Mangum
from src.api import app

handler = Mangum(app, lifespan="auto")
