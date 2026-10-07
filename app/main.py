from app.auth.routes import jwt_auth
from app.limiter import limiter
from app.models import User, Note, Tag, note_tags 
from app.routes.note import note_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = []# Add the frontend origin here when a separate frontend is introduced.
app.add_middleware(
    CORSMiddleware, 
    allow_origins= origins,
    allow_methods= ["*"],
    allow_headers= ["*"],
    allow_credentials= True
)

app.include_router(jwt_auth)
app.include_router(note_router)

@app.get("/health")
def health_test():
    return {"message": "Application running successfully"}
