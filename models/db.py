from os import getenv
from peewee import PostgresqlDatabase

# データベース接続の定義
db = PostgresqlDatabase(getenv("sample_app_DATABASE_URL"))
