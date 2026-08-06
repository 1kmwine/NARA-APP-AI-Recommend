from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ai_recommend_db_host: str = "192.168.47.105"
    ai_recommend_db_port: int = 3306
    ai_recommend_db_user: str = "ai_recommend_app"
    ai_recommend_db_password: str
    ai_recommend_db_name: str = "ai_recommend"
    wine_info_db_name: str = "wine_info"

    pos_db_host: str = "192.168.47.105"
    pos_db_port: int = 3306
    pos_db_user: str = "ai_recommend_pos_ro"
    pos_db_password: str
    pos_db_name: str = "pos"

    nas1_base_url: str = "http://el.naracellar.com/share.cgi"
    nas1_share_ssid: str

    gemini_api_key: str = ""


settings = Settings()
