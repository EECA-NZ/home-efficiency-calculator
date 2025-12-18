# Home Efficiency Calculator

![Linting](https://github.com/EECA-NZ/home-efficiency-calculator/actions/workflows/pylint.yml/badge.svg)
![Tests](https://github.com/EECA-NZ/home-efficiency-calculator/actions/workflows/python-tests.yml/badge.svg)
[Test Coverage Report](https://eeca-nz.github.io/home-efficiency-calculator/htmlcov)
[API documentation](https://home-efficiency-calculator-app.azurewebsites.net/docs)

This repository contains the source code for the [Home efficiency calculator](http://home-efficiency-calculator.australiaeast.azurecontainer.io:8000/docs), a FastAPI application designed to provide insights into household energy costs and CO2 emissions.

It is used to serve the numbers behind EECA's public-facing [Home energy savings calculator](https://www.genless.govt.nz/for-everyone/at-home/energy-saving-appliances/home-energy-savings-calculator/) web app.

We would like to thank the team behind the [Powerswitch](https://www.powerswitch.org.nz/questionnaire) tool for their generosity in sharing a national tariff dataset, which has allowed us to build regional energy pricing into our model.

Users of the [Home energy savings calculator](https://www.genless.govt.nz/for-everyone/at-home/energy-saving-appliances/home-energy-savings-calculator/) are likely to also be interested in the [Electrification calculator](https://calculate.rewiring.nz/), developed by Rewiring Aotearoa, which helps users calculate how much they could save by electrifying their household.

## About
This is a prototype for an approach to deploying our models that aims to make it easy:

* to deploy them as a Dockerized backend for our public tools, and

* to use locally as a library for research.

In either case the same codebase is used, providing a single source of truth, and allowing EECA teams to manage the model in a single place.

## Prerequisites
Before running the application, ensure you have Python and Docker installed on your system. Python 3.12 or higher is recommended.

## Local Setup
It is assumed that the user is working in a powershell environment on a Windows machine.

1. **Create and activate a virtual environment:**

    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

1. **Upgrade pip and install dependencies:**

    ```bash
    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt
    python -m pip install .  # or python -m pip install -e .
    ```

1. **Install the pre-commit hooks:**

    ```bash
    pre-commit install
    pre-commit install --hook-type pre-push
    ```

    This installs Git hooks specified in `.pre-commit-config.yaml`:

    *   On **commit**, fast checks (`black`, `isort`, and `pylint` on staged files only) are run.

    *   On **push**, thorough checks (`pylint` on the whole codebase and `pip-audit`) are run.

1. **Run the test suite:**

    ```bash
    python -m pytest --verbose
    ```

1. **Run the test suite with coverage:**

    ```bash
    python -m coverage run -m pytest
    python -m coverage report
    python -m coverage html
    ```

1. **Run pylint manually (entire codebase):**

    ```bash
    python -m pylint --disable=R0801 $(git ls-files '*.py')
    ```

1. **Run vulture manually:**

    ```bash
    python -m vulture app tests scripts
    ```

1. **Run the application locally:** Use Uvicorn to run the application with live reloading:

    ```bash
    python -m uvicorn app.main:app --reload
    ```

1. **Access the application:**
    Point your browser at `http://localhost:8000` or `http://localhost:8000/docs` to see the Swagger UI.

1. **Post a request to the API:**
    ```
    curl -Method 'POST' `
        -Uri 'http://localhost:8000/cooktop/savings' `
        -Headers @{
            "Accept"="application/json"
            "Content-Type"="application/json"
        } `
        -Body '{
            "cooktop_answers": {
                "cooktop": "Piped gas",
                "alternative_cooktop": "Electric induction"
            },
            "your_home": {
                "people_in_house": 4,
                "postcode": "9016",
            }
        }' `
        -OutFile 'response.json'
    ```

## Generating Lookup tables

For the time being we are using lookup tables (rather than the API) to configure the web tool.

To generate the lookup tables, having created and configured your virtual environment as described above,
enter the `scripts` directory and run the scripts as described in [scripts/readme.md](scripts/readme.md).

The lookup tables will be placed as CSV files within the lookup directory and can be provided to the web
team for ingestion into the web tool.

## Docker Setup

1. **Build the Docker image:**
    ```bash
    docker build -t home-efficiency-calculator .
    ```

1. **Run the Docker container:**
    ```bash
    docker run --rm -p 8000:8000 home-efficiency-calculator
    ```

## Accessing the application

* **Local web URL:** Point your browser at `http://localhost:8000` to view the application.

* **Swagger UI:** Access the Swagger UI by navigating to `http://localhost:8000/docs` where you can see and interact with the API's resources.

## Additional notes

* The Docker setup runs the application on port 8000, make sure this port is available on your machine.
* The API uses FastAPI, which provides automatic interactive API documentation (Swagger UI).

## Deploying the Container

To deploy the API as a web app, follow the instructions in [azure_web_app_instructions.md](azure_web_app_instructions.md).