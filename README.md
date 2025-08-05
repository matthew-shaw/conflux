# Mímir

This project is a modular, containerised web application that manages relationships between **people**, **teams**, **services**, and their technical **components**. It is designed to support structured ownership, improve organisational clarity, and facilitate collaboration between technical teams and business units.

Built using Python (Flask), PostgreSQL, Redis, and NGINX, it leverages Docker Compose for orchestration and encapsulation. Each part of the system is named after a figure or concept from Norse mythology, providing not only symbolic insight into its function, but also creating a narrative layer.

## Requirements

- Docker

## Getting started

### Set local environment variables

Create a `.env` file in the root of the repo and enter your specific config based on this example:

```dotenv
POSTGRES_DB=mimisbrunnr
POSTGRES_HOST=mimisbrunnr
POSTGRES_PASSWORD=smartestmanalive
POSTGRES_PORT=5432
POSTGRES_USER=mimir
REDIS_HOST=loki
REDIS_PORT=6379
SECRET_KEY=<see-below>
```

You **must** set a new `SECRET_KEY`, which is used to securely sign the session cookie and CSRF tokens. It should be a long random `bytes` or `str`. You can use the output of this Python command to generate a new key:

```shell
python -c 'import secrets; print(secrets.token_hex())'
```

### Run containers

```shell
docker compose up --watch
```

You should now have the app running on <https://localhost/>. Accept the browsers security warning due to the self-signed HTTPS certificate to continue.

## Testing

To run the tests:

```shell
python -m pytest --cov=app --cov-report=term-missing --cov-branch
```

## Build process

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

## Architecture overview

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

    subgraph Yggdrasil
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
    end
```

Each component in the architecture is named after a figure or element in Norse mythology. These names were chosen to reflect the function and behavior of the service they represent:

### Bifrost

NGINX Reverse Proxy and Static File Server

> “The burning rainbow bridge that connects Midgard (the realm of humans) to Asgard (the realm of the gods).”

- **What:** Acts as the secure HTTPS entry point to the system. It terminates TLS, routes requests to the backend (Mimir), and serves static files such as the frontend app and assets.
- **Why:** Separating static and dynamic routing at the proxy layer ensures performance, security, and scalability. NGINX is fast, battle-tested, and easily configurable.
- **Mythology:** Just as Bifrost connects realms, this component connects users to the application ecosystem.

### Mimir

Flask + Gunicorn application server

> “A wise being who guards Mimisbrunnr, the well of wisdom. Even after death, Mimir’s head continues to give advice to Odin.”

- **What:** Hosts the business logic and REST API. It processes client requests, talks to the database (Mimisbrunnr), and uses the cache (Loki) to optimize performance.
- **Why:** Flask offers flexibility and simplicity, while Gunicorn handles concurrency. This separation of concerns allows clean, testable architecture.
- **Mythology:** Like the wise Mimir, this service is the thinking core of the application—it holds and exposes the logic of the system.

### Mimisbrunnr

PostgreSQL Database

> “The Well of Wisdom beneath Yggdrasil’s roots. Odin sacrificed an eye to drink from it and gain deep knowledge.”

- **What:** Stores all persistent data in a normalised, relational model.
- **Why:** PostgreSQL is reliable, supports rich querying, and integrates well with Flask via ORMs or SQLAlchemy. Using a relational DB supports integrity and consistency in the data model.
- **Mythology:** As the well of knowledge, Mimisbrunnr is the source of all truths the application relies on.

### Loki

Redis Cache

> “The trickster god, known for speed, mischief, and unpredictability. Often at the center of both chaos and transformation.”

- **What:** Provides fast, in-memory storage for ephemeral data—used for caching, temporary tokens, session data, etc.
- **Why:** Redis is extremely fast and well-suited for performance-critical features. It decouples the persistence layer from volatile needs.
- **Mythology:** Like the unpredictable Loki, this component is fast, transient, and sometimes mischievous—but indispensable.

### Yggdrasil

Docker Compose Network

> “The World Tree, connecting the nine realms of Norse cosmology. A living system that sustains all worlds.”

- **What:** Defines the network within which all containers communicate securely and predictably.
- **Why:** Docker Compose simplifies multi-service orchestration and local development. Networking them under yggdrasil makes component communication seamless.
- **Mythology:** Yggdrasil binds all services together, enabling the flow of data and control—just as it holds together the Norse universe.

## Logical data model

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
