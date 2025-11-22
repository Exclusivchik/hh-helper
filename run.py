# run.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # В production обычно False
        workers=4,    # Количество worker процессов
        log_level="info"
    )