from pydantic_settings import BaseSettings, SettingsConfigDict


class NASConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    NAS_HOST: str
    NAS_USER: str
    NAS_PASS: str
    NAS_SHARE: str

    NAS_MOUNT_PATH: str = "/mnt/nas"
    BACKEND_API_URL: str = "http://backend:8000"
    POLL_INTERVAL_SECONDS: int = 300
    SEQ_URL: str = "http://seq:5341"


config = NASConfig()
