from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
    )

    DATABASE_URL: str

    # JWT
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_EMAIL_SECRET: str
    JWT_EMAIL_REFRESH_SECRET: str

    # Resend
    RESEND_API_KEY: str
    VERIFY_EMAIL: str
    RESET_PASSWORD_EMAIL: str

    # Frontend
    FRONTEND_HOST: str

    # Token expiration (minutes)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_TOKEN_EXPIRE_MINUTES: int = 60
    RESET_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()
