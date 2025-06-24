# NautiChat Backend

## Setup & Run

```bash
# 1. Activate virtual environment
windows: venv\Scripts\activate
macOS/Linux: source venv/bin/activate

# 2. Install dependencies
pip install -r backend-api/requirements.txt

# 3. Configure environment
cp backend-api/.env.example backend-api/.env

# 4. Start the application
export PYTHONPATH="backend-api:LLM:."
uvicorn src.main:app --reload

# 5. (Alternative) Run with Docker Compose
docker compose up --build
