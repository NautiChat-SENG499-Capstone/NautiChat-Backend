from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from src.settings import get_settings
from redis.asyncio import Redis

engine = create_engine(
    get_settings().SUPABASE_DB_URL,
    poolclass=NullPool,
    connect_args={"sslmode": "require"},  # Required for Supabase Postgres
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_redis():
    return Redis(
        host="redis-13649.crce199.us-west-2-2.ec2.redns.redis-cloud.com",
        port=13649,
        decode_responses=True,
        username="default",
        password=get_settings().REDIS_PASSWORD,
    )
