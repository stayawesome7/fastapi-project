from typing import List, Optional
from fastapi import FastAPI,Response,status,HTTPException,Depends
from fastapi.params import Body
from pydantic import BaseModel,EmailStr,BaseSettings
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from datetime import datetime
from pydantic import BaseModel
from pydantic.errors import DateTimeError
from . import utils,oauth
from .config import settings

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
#origins = ["https://www.google.com"]
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Schemas To structure strict Request format
#Therfore we can have multiple Schemas for all diff type of requests
class PostBase(BaseModel):
    title : str
    content : str
    published : bool = True

class PostCreate(PostBase):
    pass
#schemas to Structure strict Response format
#this is used to prevent spillover of unecessary info to user from DB
#Therefore structure Response
class ResPostBase(BaseModel):
    title: str
    content : str
    owner_id : int
    created_at : datetime



#DB Connection Setup
while True:
    try:
        conn = psycopg2.connect(host=f'{settings.database_hostname}',
        database=f'{settings.database_name}',user=f'{settings.database_username}',
        password=f'{settings.database_password}',cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        print("[+] DB connection established")
        break
    except Exception as error:
        print("[-] Connecting to DB failed and Error : ",error)
        time.sleep(3)
@app.get("/")
def root():
    return {"msg": "Hello World from AJ"}
###########################################################################
#posts Section

#GET ALL POSTS
#@app.get("/posts",response_model=List[ResPostBase])
@app.get("/posts")
def get_posts():
    cursor.execute("""SELECT * FROM postss""")
    #To fetch all the posts
    #posts = cursor.fetchall()
    #To calculate response along with votes
    cursor.execute("""SELECT postss.*, COUNT(votes.post_id) as likes FROM postss 
    LEFT JOIN votes on postss.id = votes.post_id group by postss.id""")
    posts = cursor.fetchall()
    return posts
 
#CREATE A POST
@app.post("/posts",status_code=status.HTTP_201_CREATED,response_model=ResPostBase)
def create_posts(post : PostCreate,current_user: int = Depends(oauth.get_current_user)):
    #Fetch current user Who has logged in for creating post
    cursor.execute("""SELECT * FROM users WHERE id = %s """, (current_user.id,))
    user = cursor.fetchone()
    print("Logged in User : " + user["email"])

    cursor.execute("""INSERT INTO postss (title,content,published,owner_id) VALUES (%s,%s,%s,%s) RETURNING *""",
    (post.title,post.content,post.published,current_user.id))
    new_post = cursor.fetchone()
    conn.commit()
    return new_post

#GET POST WITH ID
#@app.get("/posts/{id}",response_model=ResPostBase)
@app.get("/posts/{id}")
def get_post(id: int): #To validate url that user must send int not str in the url 422 or 500(internal Server Error)
    #cursor.execute("""SELECT * FROM postss WHERE id = %s """, (str(id),))
    cursor.execute("""SELECT postss.*, COUNT(votes.post_id) as likes FROM postss 
    LEFT JOIN votes on postss.id = votes.post_id where postss.id = %s group by postss.id""",(str(id),))
    post = cursor.fetchone()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post {id} not found")
    return post

#DELETE POST WITH ID
@app.delete("/posts/{id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id: int,current_user: int = Depends(oauth.get_current_user)):

    #Fetch current user Who has logged in for creating post
    cursor.execute("""SELECT * FROM users WHERE id = %s """, (current_user.id,))
    user = cursor.fetchone()
    print("Logged in User : " + user["email"])

    #Check wether post(post-id) owned by logged-in (owner-id from request) user or not
    cursor.execute("""SELECT * FROM postss WHERE id = %s """, (str(id),))
    fetched_post = cursor.fetchone()
    if fetched_post == None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id:{id} does not exist")
    
    if str(fetched_post["owner_id"]) == current_user.id:
        #DELETE OPERATION
        cursor.execute("""DELETE FROM postss WHERE id = %s returning *""",(str(id),))
        deleted_post = cursor.fetchone()
        conn.commit()
        print("Post deleted")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=f"post {id} not owned by user")
    
    return f"post {id} deleted"


#UPDATE POST WITH ID
@app.put("/posts/{id}",response_model=ResPostBase)
def update_post(id: int,post : PostCreate,current_user: int = Depends(oauth.get_current_user)):
    
    #Fetch current user Who has logged in for creating post
    cursor.execute("""SELECT * FROM users WHERE id = %s """, (current_user.id,))
    user = cursor.fetchone()
    print("Logged in User : " + user["email"])

    #Check wether post(post-id) owned by logged-in (owner-id from request) user or not
    cursor.execute("""SELECT * FROM postss WHERE id = %s """, (str(id),))
    fetched_post = cursor.fetchone()
    if fetched_post == None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"post with id : {id} does not exist")
    
    if str(fetched_post["owner_id"]) == current_user.id:
        #UPDATE OPERATION
        cursor.execute("""UPDATE postss SET title = %s,content = %s, published = %s WHERE id = %s returning *""",
        (post.title,post.content,post.published,str(id)))
        updated_post = cursor.fetchone()
        conn.commit()
        print("Post Updated")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=f"post {id} not owned by user")
    
    return updated_post

################################################################################
#Users Section
#Schemas
class UserCreate(BaseModel):
    email : EmailStr
    password : str

class ResCreateUser(BaseModel):
    email : EmailStr
    id : int
    created_at : datetime

class ResRetrieveInfo(BaseModel):
    email : EmailStr

class UserLogin(BaseModel):
    email : EmailStr
    password : str

class Token(BaseModel):
    access_token : str
    token_type : str


#create user
@app.post("/users",status_code=status.HTTP_201_CREATED,response_model=ResCreateUser)
def create_user(user : UserCreate):
    #Hashing Input Password

    hashed_password = utils.hash(user.password)
    #And update the plain password with hashed password
    user.password = hashed_password

    cursor.execute("""INSERT INTO users (email,password) VALUES (%s,%s) RETURNING *""",
    (user.email,user.password),)
    new_user = cursor.fetchone()
    conn.commit()
    return new_user

#Retrieve User Info
@app.get("/users/{id}",response_model=ResRetrieveInfo)
def get_user(id:int):
    cursor.execute("""SELECT * FROM users WHERE id = %s """, (str(id),))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"user {id} not found")
    return user

################################################################################
#Auth Section
@app.post("/login",response_model=Token)
def login(user : UserLogin):
    cursor.execute("""SELECT * FROM users WHERE email = %s""", ((user.email),))
    fetched_dbuser = cursor.fetchone()

    #Verifying Email is registered or not
    if not fetched_dbuser:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid User Credentials")
    
    #Verifying User Password
    if not utils.verify(user.password,fetched_dbuser['password']):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid Password")
    
    #Successful login Create a TOken and send a token
    access_token = oauth.create_access_token(data={"user_id":fetched_dbuser["id"]})
    return {"access_token" : access_token,"token_type":"bearer"}

################################################################################
#Vote Section

class Vote(BaseModel):
    post_id : int
    dir : int


@app.post("/vote",status_code=status.HTTP_201_CREATED)
def vote_post(vote : Vote,current_user: int = Depends(oauth.get_current_user)):
    #check for valid dir (0 or 1)
    if (vote.dir == 0 or vote.dir == 1):
        #Fetch current user Who has logged in for creating post
        print(current_user.id)

        #Check if post is avlb or not
        cursor.execute("""SELECT * FROM postss WHERE id = %s """, (vote.post_id,))
        post = cursor.fetchone()
        if not post:
            print("post not avlb")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post {vote.post_id} not found")
        else:
            #Check wether post is already liked or not
            cursor.execute("""SELECT * FROM votes WHERE post_id = %s AND user_id = %s """,(vote.post_id,current_user.id),)
            user_post_vote = cursor.fetchone()
            if user_post_vote:
                if vote.dir == 0:
                    #Delete operation
                    cursor.execute("""DELETE FROM votes WHERE post_id = %s AND user_id = %s  returning *""",
                    (vote.post_id,current_user.id),)
                    deleted_post = cursor.fetchone()
                    conn.commit()
                    return {"message" : "Successfully Disliked"}
                else:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'vote not allowed and vote already casted')
            else:
                #Caste vote
                if vote.dir == 1:
                    cursor.execute("""INSERT INTO votes (post_id,user_id) VALUES (%s,%s) RETURNING *""",
                    (vote.post_id,current_user.id),)
                    new_vote = cursor.fetchone()
                    conn.commit()
                    return {"message" : "Successfully Liked"}
                else:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'Already disliked')
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'do not fuzz appl')
        

        

