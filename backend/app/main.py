from fastapi import FastAPI

from app.routers.bracket import router as bracket_router
from app.routers.images import router as images_router
from app.routers.recommend import router as recommend_router

app = FastAPI(title="AI Wine Recommend API")
app.include_router(recommend_router)
app.include_router(bracket_router)
app.include_router(images_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
