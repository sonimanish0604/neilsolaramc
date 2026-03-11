from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "neilsolar-api"
    app_env: str = "dev"
    auth_disabled: bool = False

    database_url: str
    database_admin_url: str

    gcs_media_bucket: str = "neilsolar-dev-media"
    gcs_reports_bucket: str = "neilsolar-dev-reports"

    approval_token_ttl_hours: int = 72
    approval_retry_max_attempts: int = 3
    approval_retry_backoff_seconds: int = 300
    approval_reminder_lead_hours: int = 24
    approval_max_reminders: int = 2
    approval_link_base_url: str = "http://localhost:8000/approve"
    report_job_max_attempts: int = 3
    report_job_backoff_seconds: int = 120
    bootstrap_admin_key: str = "dev-bootstrap-key"

    @field_validator("database_url", "database_admin_url", mode="before")
    @classmethod
    def _strip_db_urls(cls, value: str) -> str:
        # Secrets copied from shell/console can accidentally include trailing spaces/newlines.
        return value.strip()


settings = Settings()
