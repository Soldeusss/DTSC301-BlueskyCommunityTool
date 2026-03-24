import uvicorn

from src.ingest import ingest_events, sample_events

uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    result = ingest_events(sample_events())
    print(result)
