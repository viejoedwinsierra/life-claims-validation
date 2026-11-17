"""Pydantic contracts for the claims HTTP API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InsuredRequest(BaseModel):
    """Insured person's identifying information."""

    model_config = ConfigDict(extra="forbid")

    tipo_documento: str = Field(min_length=1)
    numero_documento: str = Field(min_length=1)


class ClaimRequest(BaseModel):
    """Input contract for a life insurance claim."""

    model_config = ConfigDict(extra="forbid")

    id_solicitud: str = Field(min_length=1)
    canal: str = Field(min_length=1)
    numero_poliza: str = Field(min_length=1)
    asegurado: InsuredRequest
    tipo_reclamacion: str = Field(min_length=1)
    fecha_siniestro: str
    fecha_radicacion: str
    reclamante: dict = Field(default_factory=dict)
    descripcion: str = ""
    documentos_adjuntos: list = Field(default_factory=list)

    @field_validator("fecha_siniestro")
    @classmethod
    def validate_loss_date(cls, value: str) -> str:
        """Validate ISO loss date while preserving its string representation."""
        date.fromisoformat(value)
        return value

    @field_validator("fecha_radicacion")
    @classmethod
    def validate_filing_datetime(cls, value: str) -> str:
        """Accept ISO filing dates and datetimes."""
        try:
            datetime.fromisoformat(value)
        except ValueError:
            date.fromisoformat(value)
        return value
