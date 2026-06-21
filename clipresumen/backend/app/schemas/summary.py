"""Pydantic schemas for summaries.

`VideoSummary` is both the structured-output target for the Claude call and the
shape returned to the frontend, so the JSON renders directly in the UI.
"""

from pydantic import BaseModel, Field


class TimestampHighlight(BaseModel):
    """A notable moment in the video, when the transcript carries timestamps."""

    timestamp: str = Field(description="Marca de tiempo, p. ej. '12:34'.")
    description: str = Field(description="Qué ocurre en ese momento.")


class VideoSummary(BaseModel):
    """Structured summary of a YouTube video.

    Field order mirrors the format requested in the product spec:
    título → puntos clave → resumen extendido → timestamps → conclusión/CTA.
    """

    titulo: str = Field(description="Resumen de una línea del tema central.")
    puntos_clave: list[str] = Field(
        description="5-8 ideas principales, una por elemento."
    )
    resumen_extendido: str = Field(
        description="2-3 párrafos narrativos que desarrollan el contenido."
    )
    timestamps_relevantes: list[TimestampHighlight] = Field(
        default_factory=list,
        description=(
            "3-5 momentos clave si la transcripción incluye marcas de tiempo; "
            "lista vacía si no las hay."
        ),
    )
    conclusion_cta: str = Field(
        description="Qué puede hacer el espectador con esta información."
    )
