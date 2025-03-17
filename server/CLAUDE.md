# Kinetic Photo Server - Development Guide

## Build & Run Commands
- Create virtual environment: `pipenv install --dev`
- Build docker image: `make build`
- Run docker container: `./run-docker.sh`
- Run development server: `pipenv run python -m uvicorn kinetic_server.server:create_server --reload --host 0.0.0.0 --port 8080`
- Start server (production): `uvicorn kinetic_server.asgi:app --host 0.0.0.0 --port 8080`
- CLI entry point: `kinetic-photo-cli`
- Format code: `pipenv run black src/`

## Code Style Guidelines
- **Imports**: Group in order: standard library, third-party, local (separated by blank lines)
- **Type Hints**: Always use type annotations on function parameters and return values
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Docstrings**: Triple-quoted strings with Args/Returns sections for functions
- **Error Handling**: Use explicit type checking, Optional types, and defensive programming
- **Code Organization**: Prefer class-based design with dataclasses for data containers
- **Formatting**: Project uses Black formatter - maintain 88 character line length

## Project Structure
- Container-based dependency injection using dependency-injector
- FastAPI-based API server (previously Flask) with Uvicorn as ASGI server
- Google Photos integration
- Pipeline-based processing architecture for photo transformations
- API docs available at `/docs` (Swagger) and `/redoc` (ReDoc) when server is running

## Development Tips
- Regenerate setup.cfg from dependencies: `make setup.cfg`
- Ubuntu 24.04: Comment out uwsgi in Pipfile first, then install
- Version info based on git commit count and hash
- Access API documentation at http://localhost:8080/docs after starting server