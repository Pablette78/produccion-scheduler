import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine

import api.main as main_module


@pytest.fixture
def client(monkeypatch, tmp_path):
    engine_de_test = create_engine(
        f"sqlite:///{tmp_path}/test.sqlite3", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(main_module, "_engine", engine_de_test)
    with TestClient(main_module.app) as c:
        yield c
