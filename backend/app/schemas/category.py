from pydantic import BaseModel, ConfigDict, Field


class CategoryRead(BaseModel):
    # populate_by_name permet de construire l'objet en utilisant soit le
    # champ `parent_id` soit l'alias `parent_category_id` tel qu'exposé par
    # le modèle SQLAlchemy.
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    parent_id: int | None = Field(default=None, alias="parent_category_id")
