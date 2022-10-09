"""
Module to create a SQLite schema using SQLAlchemy to hold in cert_ids and match them up with 
Hubspot Instance ids that are generated everytime a new certificate is created.
"""

import os
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.ext.declarative import declarative_base


package_dir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(package_dir, 'uuid.db')

SQLITE_DB = ''.join(['sqlite:///', db_dir])

engine = create_engine(SQLITE_DB) 

Base = declarative_base()

class CertIdHistory(Base):

    __tablename__ = "cert_id_history"

    cert_id  = Column(Integer, primary_key=True)
    hs_instance_id = Column(Integer, unique=True)


Base.metadata.create_all(engine)
engine.dispose()