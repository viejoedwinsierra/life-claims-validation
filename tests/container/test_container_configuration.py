from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_exists():
    assert (ROOT / "Dockerfile").is_file()


def test_dockerfile_runs_fastapi():
    content = (ROOT / "Dockerfile").read_text()
    assert "uvicorn" in content
    assert "life_claims.api.main:app" in content


def test_dockerignore_excludes_confidential_kit():
    content = (ROOT / ".dockerignore").read_text()
    assert "kit_prueba_tecnica" in content


def test_compose_exists_and_configures_database():
    content = (ROOT / "compose.yaml").read_text()
    assert "CLAIMS_DB_PATH" in content
    assert "CORE_BASE_URL" in content


def test_container_initializes_claims_database():
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "compose.yaml").read_text()

    assert "COPY src/" in dockerfile
    assert "001_create_claims.sql" in dockerfile
    assert "life_claims.infrastructure.init_claims_db" in compose
