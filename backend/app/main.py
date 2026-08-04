from fastapi import FastAPI

app = FastAPI(title="AI Wine Recommend API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
