# Developing

First create the virtual environment:
```
pipenv install --dev
```

## Running the Server

The server uses FastAPI with Uvicorn as the ASGI server. To run the development server:

```
pipenv run python -m uvicorn kinetic_server.server:create_server --reload --host 0.0.0.0 --port 8080
```

Or use the VS Code debug configuration "Debug FastAPI".

## API Documentation

Once the server is running, you can access the auto-generated API documentation at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Ubuntu 24.04 Installation Note

If you are running Ubuntu 24.04 and get the following error during installation:
```
AttributeError: install_layout. Did you mean: 'install_platlib'
```

Try running:
```
pipenv install --dev
```