from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str = Field(description="Canonical name of the entity")
    entity_type: str = Field(
        description="Short type label: person, place, organization, product, event, or other"
    )
    summary: str = Field(description="One-sentence description based only on this conversation")


class ExtractedFact(BaseModel):
    subject: str = Field(description="Entity name; use 'user' for the human speaker")
    predicate: str = Field(
        description="Short snake_case relation, e.g. lives_in, works_at, owns, prefers, visited"
    )
    object: str = Field(description="Entity name or literal value")
    fact: str = Field(
        description="The fact restated as one standalone sentence, with relative dates resolved to absolute ones"
    )
    valid_at: str | None = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) the fact became true, if stated or inferable from context, else null",
    )
    functional: bool = Field(
        description=(
            "True if only one object can be true at a time for this subject and predicate "
            "(lives_in, works_at, is_named); false for multi-valued relations "
            "(owns, visited, purchased_from, attended)"
        )
    )


class Extraction(BaseModel):
    entities: list[ExtractedEntity]
    facts: list[ExtractedFact]
