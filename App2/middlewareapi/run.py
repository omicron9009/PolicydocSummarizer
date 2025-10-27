import uvicorn
import os

if __name__ == "__main__":
    # We point uvicorn to "app.main:app"
    # "app.main" is the file /app/main.py
    # ":app" is the FastAPI object named 'app' inside that file
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,  # Running on port 8001
        reload=True,
        log_level="info"
    )