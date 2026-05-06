from pydantic import BaseModel, ConfigDict, Field


class CategoryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    parent_category_id: int | None = None
    is_system: bool = False


class CategoryRead(BaseModel):
    # populate_by_name permet de construire l'objet en utilisant soit le
    # champ `parent_id` soit l'alias `parent_category_id` tel qu'exposé par
    # le modèle SQLAlchemy.
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    parent_id: int | None = Field(default=None, alias="parent_category_id")


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_category_id: int = Field(
        ..., description="Obligatoire : on ne crée que des sous-catégories"
    )
    color: str | None = Field(default=None, max_length=9)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=9)
