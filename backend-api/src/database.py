from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

############################################################
# User Database
############################################################



############################################################
# LLM: Conversation Database
############################################################
CONVERSTATION_DATABASE_URL = "sqlite:///./conversation.db"
conv_engine = create_engine(CONVERSTATION_DATABASE_URL)
ConvSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=conv_engine)
ConvBase = declarative_base()