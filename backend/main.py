from fastapi import FastAPI
from database import Base, engine
from routers import health, auth, users

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)