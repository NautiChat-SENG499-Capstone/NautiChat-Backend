# NautiChat Backend

## Territorial Acknowledgements

We acknowledge with respect that the Cambridge Bay coastal community observatory is located on the lands and in the waters of the Inuit, in Iqaluktuuttiaq (Cambridge Bay) in the Kitikmeot Region of Nunavut.

We also acknowledge with respect the Lekwungen peoples on whose traditional territory the University of Victoria stands, and the Songhees, Esquimalt and W̱SÁNEĆ peoples whose historical relationships with the land continue to this day.

## Project Overview

NautiChat is a conversational AI assistant built with FastAPI for Ocean Networks Canada. It allows users to query and download real-time and historical oceanographic data via natural language. Designed for researchers, educators, students, and coastal communities to make ocean data more accessible and understandable.

### Key Features
- Natural language queries for ocean data
- Real-time and historical data access
- Multi-format data export capabilities
- User authentication and session management
- Admin dashboard for content management
- Semantic search powered by vector embeddings
- Feedback system for continuous improvement

## Architecture

### Tech Stack
- **Backend Framework**: FastAPI (Python 3.11+)
- **LLM Provider**: Groq Cloud API
- **Vector Database**: Qdrant for semantic search
- **Primary Database**: PostgreSQL (hosted on Supabase)
- **Embeddings**: Jina AI
- **External API**: Ocean Networks Canada (ONC) API
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest with SQLite for test isolation
- **Deployment**: UVic Virtual Machine with CloudFlare Zero Trust Tunneling


### System Architecture
TO DO: add my new diagram here

## Getting Started

### Prerequisites
- Python 3.11 or higher
- PostgreSQL (or use Docker)
- Qdrant vector database
- Valid API keys for:
  - Groq Cloud
  - Jina AI
  - Ocean Networks Canada
  - Supabase (if using hosted PostgreSQL)
**If setting up migrations for the first time:**
```bash
alembic init alembic
```

### Installation

#### Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/NautiChat-SENG499-Capstone/NautiChat-Backend.git
cd NautiChat-Backend

# 2. Create and activate virtual environment
# Windows:
python -m venv venv
venv\Scripts\activate

# macOS/Linux:
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp backend-api/.env.example backend-api/.env
# Edit .env with your configuration

# 5. Set Python path
export PYTHONPATH="backend-api:LLM:."

# 6. Run Alembic database migrations
alembic upgrade head

# 7. Start the application
uvicorn src.main:app --reload
```

#### Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up --build

# Run in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## CI/CD Pipeline

This project uses GitHub Actions for continuous integration and delivery. All pull requests and pushes to `main` go through the following stages:

### Lint (pre-commit with Ruff)

- Runs `pre-commit` using [ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Fixes import ordering and code style issues (`--select I`, `--fix`)
- Enforces consistent code quality across the codebase

### Test (Pytest)

- Executes the full test suite using `pytest` and `pytest-asyncio`
- Uses a mocked SQLite database and secret environment variables
- Avoids hitting external APIs by mocking dependencies

### Docker Build (Pull Requests)

- Builds the Docker image locally to validate Dockerfile correctness
- Does not push to Docker Hub
- Ensures containerization remains functional before merge

### Docker Build & Push (Main Branch)

- Builds and pushes Docker images to Docker Hub:
  - `milesssssss/nautichat-backend:latest`
  - `milesssssss/nautichat-backend:<commit-sha>`
- Uses layer caching via GitHub Actions to speed up rebuilds
- Only runs when changes are pushed to `main`

Workflow logic is defined in `.github/workflows/ci.yml`.


### Pre-commit Hooks

The project uses pre-commit to maintain code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest test/test_auth.py

# Run with verbose output
pytest -v
```

### Test Configuration
- Tests use SQLite instead of PostgreSQL for isolation and speed
- Mock external API calls to avoid dependencies

## API Documentation

### Interactive Documentation
NautiChat exposes a RESTful API with interactive documentation:

- **Production**: `http://nautichat-backend-tunnel-fun.shop/docs`
- **Local Swagger UI**: `http://localhost:8000/docs`
- **Local ReDoc**: `http://localhost:8000/redoc`

### API Endpoints

#### Default
- `GET /` — Welcome message and API info
- `GET /health` — Health check with service status

#### Authentication (`/auth`)
- `POST /auth/login` — Login with email/password
- `POST /auth/guest-login` — Create guest session
- `POST /auth/register` — Register new user account
- `GET /auth/me` — Get current user profile
- `PUT /auth/me` — Update user profile
- `PUT /auth/me/password` — Change user password
- `DELETE /auth/me/delete` — Delete user account

#### LLM Chat (`/llm`)
- `GET /llm/conversations` — List users conversations
- `POST /llm/conversations` — Create new conversation
- `GET /llm/conversations/{id}` — Get conversation details
- `DELETE /llm/conversations/{id}` — Delete conversation
- `POST /llm/messages` — Send message and get AI response
- `GET /llm/messages/{id}` — Get specific message
- `PATCH /llm/messages/{id}/feedback` — Submit feedback (helpful/not helpful)

#### Admin (`/admin`)
- `POST /admin/create` — Create admin user
- `GET /admin/users` — List all users (paginated)
- `DELETE /admin/users/{id}` — Delete user by ID
- `GET /admin/messages` — Get all messages with filters
- `GET /admin/messages/clustered` — Get messages grouped by similarity
- `POST /admin/documents/raw-data` — Upload raw text for knowledge base
- `POST /admin/documents/pdf` — Upload PDF document
- `POST /admin/documents/json` — Upload structured JSON data
- `GET /admin/documents` — List all documents
- `GET /admin/documents/{source}` — Get document by source
- `DELETE /admin/documents/{source}` — Delete document


## Deployment

The backend runs on a UVic-provided VM, secured with a jumphost (Netlink ID required) and Cloudflare Zero Trust Tunneling to allow access off of UVic servers.

- **SSH Access (VS Code or terminal):**  
  Connect using your Netlink ID via the jumphost (`seng499.seng.uvic.ca`) and then to your group VM (`seng499-group3`).  

  Your ssh/config file should look something like:

    ```ssh
    Host Group3
        HostName seng499-group3 
        User NetlinkID
        ProxyJump NetlinkID@seng499.seng.uvic.ca
        IdentityFile ~/.ssh/seng499-group3
    ```

- **On the VM:**  
  1. Clone/pull from main in case the Docker Compose file has changed:  
     `git pull`
  2. Ensure your `.env` is up to date.
  3. Deploy with Docker Compose:  
     `docker compose up --build -d`
  4. View logs:  
     `docker compose logs -f`
  5. Stop services:  
     `docker compose down`

**Note:**  
The VM is not accessible from outside UVic without VPN or Zero Trust access.

For deployment issues, check logs and ensure all environment variables are set.


## Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- Ocean Networks Canada for data access and support
- All contributors and community members
- SENG 499 Teaching Team and students!

---

Built by the NautiChat team