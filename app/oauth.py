from typing import Optional
from jose import JWTError, jwt
from datetime import datetime,timedelta
from pydantic.main import BaseModel
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, oauth2
from .config import settings
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')


SECRET_KEY = f"{settings.secret_key}"
ALGORITHM = f"{settings.algorithm}"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data : dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt


class TokenData(BaseModel):
    id : Optional[str] = None

def verify_access_token(token : str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY,algorithms=[ALGORITHM])
        id : str = payload.get("user_id")
        if id is None:
            raise credentials_exception
        token_data = TokenData(id=id)    
    except JWTError as e:
        print(e)
        raise credentials_exception
    except AssertionError as e:
        print(e)    
    return token_data

def get_current_user(token : str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
    detail=f"Could not validate credentials",headers={"WWW-Authenticate":"Bearer"})

    return verify_access_token(token,credentials_exception)


