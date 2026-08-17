from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth
from routers.webapp import router as webapp
from routers.payment import router as payment
from routers.scan import router as scan

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # ishlab chiqishda hammasi ochiq; prod'da domenlarni yozing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth)
app.include_router(webapp)
app.include_router(payment)
app.include_router(scan)


@app.get("/devguard")
async def devguard():
    return {"message":"running..."}