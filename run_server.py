import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "llama_service:app",  # points to your FastAPI app in llama_service.py
        host="0.0.0.0",       # accessible from any IP on your machine/network
        port=5002,            # choose any port you like
        reload=True           # auto-reload on code changes (useful for dev)
    )
