from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables or the .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=480, ge=1)

    # Comma-separated list of exact origins, e.g. "https://www.example.com"
    cors_origins: str

    refill_rate_limit_per_minute: int = Field(default=5, ge=1)
    login_rate_limit_per_minute: int = Field(default=10, ge=1)

    @field_validator("cors_origins")
    @classmethod
    def _validate_origins(cls, value: str) -> str:
        origins = [o.strip().rstrip("/") for o in value.split(",") if o.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS must contain at least one origin")
        for origin in origins:
            if origin == "*":
                raise ValueError("CORS_ORIGINS must list your site explicitly, not '*'")
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"CORS origin must start with http:// or https://: {origin}")
        return ",".join(origins)

    @property
    def cors_origin_list(self) -> list[str]:
        return self.cors_origins.split(",")


settings = Settings()
