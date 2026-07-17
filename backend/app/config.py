from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+pg8000://postgres:postgres@localhost:5432/worth_rises"
    use_cloud_sql_connector: bool = False
    cloud_sql_instance: str = ""
    db_user: str = "postgres"
    db_pass: str = ""
    db_name: str = "worth_rises"
    jurisdictions_db_name: str = "worth_rises_jurisdictions"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    google_places_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
