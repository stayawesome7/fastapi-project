from passlib.context import CryptContext
#For Hashing Defining context
pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")

#Own Hashing Wrappre function
def hash(password : str):
    #hashing function utlised
    return pwd_context.hash(password)

def verify(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)