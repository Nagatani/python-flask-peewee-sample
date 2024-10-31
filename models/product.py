from peewee import Model, CharField, DecimalField
from .db import db

class Product(Model):
    name = CharField()
    price = DecimalField()

    class Meta:
        database = db