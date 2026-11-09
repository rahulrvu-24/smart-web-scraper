import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import ExtractionSchema
from app.schemas.extraction_schema import SchemaCreate, SchemaRead

router = APIRouter(prefix="/schemas", tags=["schemas"])


def _get_owned(db: DbSession, user: CurrentUser, schema_id: uuid.UUID) -> ExtractionSchema:
    schema = db.get(ExtractionSchema, schema_id)
    if schema is None or schema.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Schema not found")
    return schema


def _name_taken(db: DbSession, user: CurrentUser, name: str, exclude: uuid.UUID | None = None) -> bool:
    query = select(ExtractionSchema.id).where(ExtractionSchema.user_id == user.id, ExtractionSchema.name == name)
    if exclude is not None:
        query = query.where(ExtractionSchema.id != exclude)
    return db.scalar(query) is not None


@router.get("", response_model=list[SchemaRead])
def list_schemas(db: DbSession, user: CurrentUser) -> list[ExtractionSchema]:
    return list(
        db.scalars(
            select(ExtractionSchema).where(ExtractionSchema.user_id == user.id).order_by(ExtractionSchema.name)
        )
    )


@router.post("", response_model=SchemaRead, status_code=status.HTTP_201_CREATED)
def create_schema(body: SchemaCreate, db: DbSession, user: CurrentUser) -> ExtractionSchema:
    if _name_taken(db, user, body.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="You already have a schema with this name")
    schema = ExtractionSchema(
        user_id=user.id,
        name=body.name,
        description=body.description,
        fields={k: v.model_dump() for k, v in body.fields.items()},
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)
    return schema


@router.get("/{schema_id}", response_model=SchemaRead)
def get_schema(schema_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ExtractionSchema:
    return _get_owned(db, user, schema_id)


@router.put("/{schema_id}", response_model=SchemaRead)
def update_schema(schema_id: uuid.UUID, body: SchemaCreate, db: DbSession, user: CurrentUser) -> ExtractionSchema:
    schema = _get_owned(db, user, schema_id)
    if _name_taken(db, user, body.name, exclude=schema.id):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="You already have a schema with this name")
    schema.name = body.name
    schema.description = body.description
    schema.fields = {k: v.model_dump() for k, v in body.fields.items()}
    schema.version += 1
    db.commit()
    db.refresh(schema)
    return schema


@router.delete("/{schema_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schema(schema_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Response:
    db.delete(_get_owned(db, user, schema_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
