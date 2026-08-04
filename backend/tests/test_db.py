from app.db import build_db_url


def test_build_db_url_uses_pymysql_driver():
    url = build_db_url(
        host="192.168.47.105", port=3306, user="ai_recommend_app",
        password="p@ss", database="ai_recommend",
    )
    assert url == "mysql+pymysql://ai_recommend_app:p%40ss@192.168.47.105:3306/ai_recommend?charset=utf8mb4"
