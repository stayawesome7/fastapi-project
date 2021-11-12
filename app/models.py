from sqlalchemy import Column,Integer
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.sqltypes import Boolean, String
from .database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer,primary_key=True,nullable=False)
    title = Column(String,nullable=False)
    content = Column(String,nullable=False)
    published= Column(Boolean,default=True)

#models.py is SQLALCHEMY ORM 
# i ahve not utilised ORM
#so this file has no role to play