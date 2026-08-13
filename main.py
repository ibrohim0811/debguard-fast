from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # ishlab chiqishda hammasi ochiq; prod'da domenlarni yozing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth)


@app.get("/devguard")
async def devguard():
    return {"message":"running..."}