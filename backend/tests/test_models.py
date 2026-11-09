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