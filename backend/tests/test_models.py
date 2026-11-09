from app.models import Base

def _constraint_names(table_name: str) -> set[str]:
    return {c.name for c in Base.metadata.tables[table_name].constraints}


def test_users_table_is_registered():
    assert "users" in Base.metadata.tables


def test_users_columns():
    users = Base.metadata.tables["users"]
    assert set(users.columns.keys()) == {
        "id",
        "email",
        "hashed_password",
        "full_name",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert users.c.email.nullable is False
    assert users.c.full_name.nullable is True


def test_users_email_is_unique():
    assert "uq_users_email" in _constraint_names("users")

def _foreign_key(table_name: str, column: str):
    (fk,) = Base.metadata.tables[table_name].c[column].foreign_keys
    return fk


def test_api_keys_belong_to_a_user_and_cascade_on_delete():
    fk = _foreign_key("api_keys", "user_id")
    assert fk.target_fullname == "users.id"
    assert fk.ondelete == "CASCADE"


def test_api_key_hash_is_unique():
    assert "uq_api_keys_key_hash" in _constraint_names("api_keys")


def test_schema_names_are_unique_per_user():
    assert "uq_extraction_schemas_user_id_name" in _constraint_names("extraction_schemas")
    fk = _foreign_key("extraction_schemas", "user_id")
    assert fk.ondelete == "CASCADE"

def test_job_status_values_are_lowercase_strings():
    from app.models import JobStatus

    assert [s.value for s in JobStatus] == ["queued", "running", "succeeded", "failed"]
    assert Base.metadata.tables["scrape_jobs"].c.status.type.enums == [
        "queued",
        "running",
        "succeeded",
        "failed",
    ]


def test_deleting_a_schema_keeps_its_jobs():
    fk = _foreign_key("scrape_jobs", "schema_id")
    assert fk.target_fullname == "extraction_schemas.id"
    assert fk.ondelete == "SET NULL"


def test_one_result_per_job():
    assert "uq_scrape_results_job_id" in _constraint_names("scrape_results")
    assert _foreign_key("scrape_results", "job_id").ondelete == "CASCADE"