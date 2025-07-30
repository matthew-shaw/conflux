# Mímir

![Static Badge](https://img.shields.io/badge/GOV.UK%20Frontend-v5.11.0-blue)

## Requirements

- Docker

## Getting started

### Set local environment variables

Create a `.env` file in the root of the repo and enter your specific config based on this example:

```dotenv
CONTACT_EMAIL=[contact email]
CONTACT_PHONE=[contact phone]
DEPARTMENT_NAME=Mash Software
DEPARTMENT_URL=https://www.mashsoftware.com/
POSTGRES_DB=mimisbrunnr
POSTGRES_HOST=mimisbrunnr
POSTGRES_PASSWORD=smartestmanalive
POSTGRES_PORT=5432
POSTGRES_USER=mimir
REDIS_HOST=loki
REDIS_PORT=6379
SECRET_KEY=
SERVICE_NAME=Mímir
SERVICE_PHASE=Alpha
```

You **must** set a new `SECRET_KEY`, which is used to securely sign the session cookie and CSRF tokens. It should be a long random `bytes` or `str`. You can use the output of this Python command to generate a new key:

```shell
python -c 'import secrets; print(secrets.token_hex())'
```

### Run containers

```shell
docker compose up --build --watch
```

You should now have the app running on <https://localhost/>. Accept the browsers security warning due to the self-signed HTTPS certificate to continue.

## Testing

To run the tests:

```shell
python -m pytest --cov=app --cov-report=term-missing --cov-branch
```

## Build

This project uses Docker Compose to provision containers:

```mermaid
flowchart TB
    compose(compose.yml)
    nginx(nginx:stable-alpine)
    node(node:jod-alpine)
    postgres(postgres:17-alpine)
    python(python:3.13-slim)
    redis(redis:7-alpine)

    compose -- Creates --> Mimir & Loki & Bifrost & Mimisbrunnr
    Mimir -- Depends on --> Loki & Mimisbrunnr
    Bifrost -- Depends on --> Mimir

    subgraph Bifrost
        direction TB
        node -- COPY /dist /static --> nginx
    end

    subgraph Mimir
        python
    end

    subgraph Mimisbrunnr
        postgres
    end

    subgraph Loki
        redis
    end
```

## Environment

```mermaid
flowchart TB
    redis(Redis)
    client(Client)
    nginx(NGINX)
    flask(Gunicorn/Flask)
    static@{ shape: lin-cyl, label: "Static files" }
    db@{ shape: cyl, label: "PostgreSQL" }

    client -- https:443 --> nginx -- http:5000 --> flask -- postgres:5432 --> db
    flask -- redis:6379 --> redis

    subgraph Bifrost
        nginx -- Read --> static
    end

    subgraph Mimir
        flask
    end

    subgraph Mimisbrunnr
        db
    end

    subgraph Loki
        redis
    end
```

## Data model

```mermaid
erDiagram
    roles {
        UUID id PK
    }

    people {
        UUID id PK
        UUID role_id FK
        UUID team_id FK
    }

    teams {
        UUID id PK
    }

    services {
        UUID id PK
        UUID team_id FK
    }

    components {
        UUID id PK
    }

    roles ||--|{ people : "performed by"
    teams ||--o{ people : "has members"
    teams ||--o{ services : "owns"
    services ||--|{ components : "uses"
    components ||--|{ services : "used by"
```
