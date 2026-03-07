"""Pydantic schemas for backup/restore validation."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class BackupMetadata(BaseModel):
    """Metadata for backup file."""

    exported_at: datetime
    version: str = Field(pattern=r"^\d+\.\d+$")  # e.g., "1.0", "2.0"
    app_version: str | None = None  # Application version that created backup
    record_counts: dict[str, int] | None = None  # Number of records per table


class BackupData(BaseModel):
    """Data structure for backup file tables."""

    app_settings: list[dict] = Field(default_factory=list)
    family_members: list[dict] = Field(default_factory=list)
    task_lists: list[dict] = Field(default_factory=list)
    task_recurrence_series: list[dict] = Field(default_factory=list)
    task_recurrence_series_members: list[dict] = Field(default_factory=list)
    tasks: list[dict] = Field(default_factory=list)
    task_members: list[dict] = Field(default_factory=list)
    recurrence_series: list[dict] = Field(default_factory=list)
    recurrence_series_members: list[dict] = Field(default_factory=list)
    agenda_events: list[dict] = Field(default_factory=list)
    agenda_event_members: list[dict] = Field(default_factory=list)
    meals: list[dict] = Field(default_factory=list)
    photos: list[dict] = Field(default_factory=list)


class BackupFile(BaseModel):
    """Complete backup file structure."""

    exported_at: datetime
    version: str
    app_version: str | None = None
    record_counts: dict[str, int] | None = None
    data: BackupData

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format is X.Y."""
        parts = v.split(".")
        if len(parts) != 2:
            raise ValueError("Version must be in format X.Y")
        try:
            int(parts[0])
            int(parts[1])
        except ValueError as e:
            raise ValueError("Version parts must be integers") from e
        return v


class RestoreValidationResult(BaseModel):
    """Result of dry-run validation."""

    valid: bool
    version: str
    exported_at: datetime
    record_counts: dict[str, int]
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RestoreResult(BaseModel):
    """Result of restore operation."""

    status: str
    message: str
    records_imported: dict[str, int] | None = None
    pre_restore_backup_file: str | None = None
