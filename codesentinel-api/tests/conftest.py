import os
os.environ["DATABASE_URL"] = "sqlite:///./test_codesentinel.db"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base, get_db
from app.main import app

@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    def override():
        db = factory()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override
    yield factory
    app.dependency_overrides.clear()

@pytest.fixture()
def client(db_session):
    with TestClient(app) as test_client: yield test_client
