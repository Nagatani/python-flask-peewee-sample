from peewee import Model, CharField, IntegerField
from .db import db

class User(Model):
    name = CharField()
    age = IntegerField()

    class Meta:
        database = db