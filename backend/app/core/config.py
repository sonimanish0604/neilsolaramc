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
    approval_base_url: str = "https://app.neilsolar.com/approve"
    approval_link_base_url: str | None = None
    approval_retry_max_attempts: int = 3
    approval_retry_backoff_seconds: int = 300
    approval_reminder_lead_hours: int = 24
    approval_max_reminders: int = 2
    bootstrap_admin_key: str = "dev-bootstrap-key"

    twilio_enabled: bool = False
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str = "whatsapp:+14155238886"
    twilio_request_timeout_seconds: int = 10

    pdf_brand_label: str = "NEIL Solar AMC"
    report_storage_backend: str = "AUTO"
    local_reports_dir: str = "/tmp/neilsolar-reports"
    report_job_max_attempts: int = 3
    report_job_backoff_seconds: int = 120

    notification_poll_interval_seconds: int = 5
    notification_batch_size: int = 20
    notification_retry_max_attempts: int = 3
    notification_retry_delay_seconds: int = 60
    notification_archive_interval_seconds: int = 3600
    notification_purge_interval_seconds: int = 86400
    notification_maintenance_run_once: bool = False
    notification_retention_active_days_default: int = 7
    notification_retention_history_days_default: int = 365
    notification_retention_dead_letter_days_default: int = 365
    notification_purge_after_deactivation_days_default: int = 90

    secret_provider: str = "ENV"
    secret_fail_open: bool = True
    secret_cache_ttl_seconds: int = 300
    secret_fetch_timeout_seconds: int = 10
    vault_addr: str | None = None
    vault_token: str | None = None
    vault_mount: str = "secret"
    vault_kv_version: int = 2
    gcp_project_id: str | None = None

    notification_email_enabled: bool = False
    notification_email_primary_provider: str = "MAILGUN"
    notification_email_secondary_provider: str | None = "TWILIO"
    notification_email_secondary_failover_enabled: bool = False
    notification_email_from: str = "no-reply@neilsolar.local"
    notification_email_smtp_host: str = "smtp.gmail.com"
    notification_email_smtp_port: int = 587
    notification_email_smtp_user: str | None = None
    notification_email_smtp_password: str | None = None
    notification_email_smtp_ssl: bool = False
    notification_email_smtp_starttls: bool = True
    notification_mailgun_enabled: bool = False
    notification_mailgun_domain: str | None = None
    notification_mailgun_api_key: str | None = None
    notification_mailgun_api_key_secret: str | None = None
    notification_mailgun_eu_region: bool = False
    notification_mailgun_timeout_seconds: int = 10
    notification_twilio_email_enabled: bool = False
    notification_twilio_sendgrid_api_key: str | None = None
    notification_twilio_sendgrid_api_key_secret: str | None = None
    notification_twilio_sendgrid_timeout_seconds: int = 10
    notification_email_smtp_password_secret: str | None = None
    twilio_auth_token_secret: str | None = None

    notification_dev_default_recipient_email: str | None = None
    notification_dev_default_recipient_whatsapp: str | None = None

    @field_validator("database_url", "database_admin_url", mode="before")
    @classmethod
    def _strip_db_urls(cls, value: str) -> str:
        return value.strip()


settings = Settings()
