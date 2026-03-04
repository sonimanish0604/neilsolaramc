from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "allsolar-api"
    app_env: str = "dev"
    auth_disabled: bool = False

    database_url: str
    database_admin_url: str

    gcs_media_bucket: str = "allsolar-dev-media"
    gcs_reports_bucket: str = "allsolar-dev-reports"

    approval_token_ttl_hours: int = 72


settings = Settings()