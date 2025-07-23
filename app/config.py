import os

# filepath: c:\Users\Frankel\hackathon\UniPlanBj\app\config.py
class Config:
    SECRET_KEY = 'un_secret_unique_et_long_ici'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:Cyrusgnl2007@localhost/UNIPLANBJ'
    SQLALCHEMY_TRACK_MODIFICATIONS = False