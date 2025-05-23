"""
Main module to run the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, responses

from .api.checkbox_behaviour_endpoint import router as checkbox_behaviour_router
from .api.component_savings_endpoints import router as component_savings_router
from .api.fixed_cost_savings_endpoint import router as fixed_cost_savings_router
from .api.solar_savings_endpoint import router as solar_savings_router
from .api.user_geography_endpoint import router as user_geography_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Lifespan event handler to run logic on startup and shutdown.
    """
    # Startup logic
    logger.info("Application %s is starting...", app_instance)
    print("Visit http://localhost:8000 or http://127.0.0.1:8000 to access the app.")
    yield  # This allows the application to run
    # Shutdown logic
    logger.info("Application is shutting down...")


# Pass the lifespan handler when creating the FastAPI instance
app = FastAPI(
    title="Home Energy Savings Calculator",
    version="0.3.0",
    description="API for estimating household energy and emissions savings.",
    lifespan=lifespan,
)


@app.get("/")
def main():
    """
    Function to redirect to the documentation.
    """
    return responses.RedirectResponse(url="/docs/")


app.include_router(user_geography_router)
app.include_router(checkbox_behaviour_router)
app.include_router(component_savings_router)
app.include_router(solar_savings_router)
app.include_router(fixed_cost_savings_router)


def run():
    """
    Function to run the Uvicorn server.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
