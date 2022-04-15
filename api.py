# use python-3.8.10
#run using:
#uvicorn signup_test:app --reload

from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi_sqlalchemy import DBSessionMiddleware, db
from datetime import datetime, timezone
# from starlette.responses import  RedirectResponse #for redirecting to another internal URL

# import os
# from dotenv import load_dotenv
# load_dotenv('env')#load database details from .env file
import bcrypt 
import re
import uvicorn
import env

#for mailing
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

#imports from our files
from auth import AuthHandler
from model import User as ModelUser
from model import Password_tokens
from schema import User as SchemaUser
from schema import LoginSchema
from schema import PasswordResetSchema,PasswordChangeSchema
from schema import EmailSchema



app = FastAPI()

# # to avoid csrftokenError/cookie related error
app.add_middleware(DBSessionMiddleware, db_url =  env.DATABASE_URL)

#make an object of the AuthHandler class from the auth.py file
auth_handler = AuthHandler()



@app.get("/")
async def root():
    return {"message": "hello world"}

#validate the user, check if the details entered by the user can be used for making a new account
def validate_user(user:ModelUser):
    """
    Checks if email id already exists, is valid and passowrd in greater than 6 chararcters. Takes ModelUser as input
    """
    
    if(bool(db.session.query(ModelUser).filter_by(email = user.email).first())):
        raise HTTPException(status_code=400, detail='Mail already exists')

    elif not (re.fullmatch(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+', user.email)):
        raise HTTPException(status_code=400, detail='Enter valid email')

    elif (len(user.password) < 7):
        raise HTTPException(status_code=400, detail='Password must be greater than 6 characters')

    else:
        return True


@app.post("/signup/", status_code=201 )
async def signup(user: SchemaUser):
    """
    Validates user details and enters all details including hashed password to the database, takes User from schema.py as input.
    Returns error message if any problem, Signup Successful message if successful.
    """
    #if the details entered by the user are invalid, then return respective Exception using the self-defined validate_user function
    validated_user = validate_user(user)
    if (validated_user != True): 
        return validated_user

    #else register the user by adding its details to the database
    else:
        #create a hashed/encrypted password using bcrypt
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        #create a ModelUser instance with the details entered
        db_user = ModelUser(email = user.email, password = hashed_password.decode('utf-8'), first_name = user.first_name, last_name = user.last_name, created_at = datetime.now(timezone.utc))
        #add the ModelUser object(db_user) to the database
        db.session.add(db_user)
        db.session.commit()
        return {'message': "Signup Successful"}


#get details of the user if the email_id entered is valid, else return False
async def get_user_by_email(my_email: str):
    """
    Checks if the email exists in the DB. If not, returns false. If it does, returns all details of the user in User Model form from models.py.
    """
    user = db.session.query(ModelUser).filter_by(email=my_email).first()
    #if email id does not exist in the db, return false
    if(user == None):
        return False
    #return all details of the user
    return ModelUser(id = user.id, email=user.email, password=user.password, first_name=user.first_name, last_name = user.last_name, created_at=user.created_at)

@app.post("/login/")
async def authenticate_user(input_user: LoginSchema):
    user = await get_user_by_email(input_user.email)

    if (not user) or (not bcrypt.checkpw(input_user.password.encode('utf-8'), user.password.encode('utf-8'))):
        raise HTTPException(status_code=401, detail='Invalid username or password')

    else:       
        #generate/encode and return JWT token 
        token = auth_handler.encode_token(input_user.email)
        return {'token':token, 'message': 'Details are correct'}#valid for 1 minute and 30 seconds


@app.get('/protected')
def protected(request: Request, email = Depends(auth_handler.auth_wrapper)):
    """
    The auth.py file has the function auth_wrapper which validates the token by decoding it and checking the credentials.
    Using that function , the details can only be accessed if there is valid JWT token in the header
    This function is to demonstrate that
    curl --header "Authorizaion: Bearer entertokenhere" localhost:8000/protected
    """
    return {'email': email}


def send_mail(my_uuid:str):
    """
    send password reset email to user via sendgrid.
    """
    # gmail id:testforfastapi@gmail.com, password:testforfastapi@99(or 00)
    # sendgrid id:gmailid, password:forfastapitest@99(or 00)

    message = Mail(
    from_email='testforfastapi@gmail.com',
    to_emails='testforfastapi@gmail.com',
    subject='Password Reset',
    html_content = 'Hello! <p> Your UUID is:<p> 127.0.0.1:8000/reset_password_link/' + str(my_uuid) +"<p> The link will expire in 10 minutes.")
    try:
        sg = SendGridAPIClient('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')
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
        return {'message': 'Link sent, please check mail'}
    except Exception as e:
        raise HTTPException(status_code=400, detail='Sorry!We could not send the link right now')


@app.post('/request_change_password')
async def req_change_password(email_schema: EmailSchema):
    
    
    my_email = email_schema.email
    #check if the user exists in the users database
    user = db.session.query(ModelUser).filter_by(email = my_email).first()
    #if email id does not exist in the db, return false
    if(user == None):
        return {'message': 'The user is not registered'}
    my_id = user.id

    #if the user exists, generate uuid
    u = uuid4()

    #add the id, uuid and generated time to password_tokens database and add the ModelUser object(db_user) to the database
    db_user = Password_tokens(id = my_id, uuid = str(u), time = datetime.now(timezone.utc), used = False)
    
    db.session.merge(db_user)
    db.session.commit()
    
    #send email
    return send_mail(u)    
    # return user



def get_uuid_details(my_uuid:str):
    """
    get id and time generated of the entered uuid
    """
    try:
        user = db.session.query(Password_tokens).filter_by(uuid = str(my_uuid)).first()
    except:
        raise HTTPException(status_code=400, detail='UUID entered incorrectly')

    #if email id does not exist in the db, return false
    if(user == None):
        raise HTTPException(status_code=400, detail='UUID not found')
    #return all details of the user
    return Password_tokens(id = user.id, uuid = my_uuid, time = user.time, used = user.used)


# get details of the user if the email_id entered is valid, else return False
async def get_user_by_id(my_id: int):
    user = db.session.query(ModelUser).filter_by(id = my_id).first()
    #if email id does not exist in the db, return false
    if(user == None):
        return False
    #return all details of the user
    return ModelUser(id = my_id, email=user.email, password=user.password, first_name=user.first_name, last_name = user.last_name, created_at = user.created_at)



@app.post('/reset_password_link')
async def reset_password_link(my_uuid:str,ps:PasswordResetSchema):
    #get id,uuid and genreated time of token via method get_uuid_details
    uuid_details = get_uuid_details((my_uuid))

    if(uuid_details.used == True):
        raise HTTPException(status_code=400, detail='Link already used once')

    mins_passed = ((datetime.now(timezone.utc) - uuid_details.time).seconds)/60
    if(mins_passed > 10):
        raise HTTPException(status_code=401, detail = 'More than 10 minutes have passed')
    else:
        new_user = await get_user_by_id(uuid_details.id)
        #get and hash password if both passwords same
        if(ps.password == ps.confirm_password): 
            if(len(ps.password) < 7):
                raise HTTPException(status_code=401, detail = 'Passwords length < 7')
            else:
                new_user.password =  bcrypt.hashpw(ps.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                # #create a ModelUser instance with the details entered
                # db_user = ModelUser(id = uuid_details.id, email = new_user.email, password = hashed_password.decode('utf-8'), first_name = new_user.first_name, last_name = new_user.last_name, created_at = new_user.created_at)
                # #update the hashed password in the database
                # db_user.password = hashed_password.decode('utf-8
                # #add/merge the ModelUser object(db_user) to the database
                db.session.merge(new_user)
                db.session.commit()

                #update uuid details
                uuid_details.used = True
                db.session.merge(uuid_details)
                db.session.commit()
                return {'message':'password change sucessful'}    
        else:
            raise HTTPException(status_code=401, detail = 'Passwords are not same')

@app.post('/change_password')
async def change_password(ps:PasswordChangeSchema, my_email = Depends(auth_handler.auth_wrapper) ):
    """
    To change password  when the user is logged in. Needs PasswordChangeSchema and JWT token as input parameters. 
    Returns sucessful message if success, otherwise raises error 401.
    
    """
    user = await get_user_by_email(my_email)
    my_id = user.id
    actual_password = user.password.encode('utf-8')

    if(bcrypt.checkpw(ps.current_password.encode('utf-8'), actual_password)):
        if(ps.new_password == ps.confirm_password and len(ps.new_password) > 6 and ps.new_password != ps.current_password):
            user.password =  bcrypt.hashpw(ps.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            #create a ModelUser instance with the details entered
            # db_user = ModelUser(id = my_id, email = user.email, password = hashed_password.decode('utf-8'), first_name = user.first_name, last_name = user.last_name, created_at = user.created_at)
            # #update the hashed password in the database
            # #add/merge the ModelUser object(db_user) to the database
            db.session.merge(user)
            # db.session.query(ModelUser).filter_by(id = my_id).update({ModelUser.password : hashed_password.decode('utf-8')}, synchronize_session = False)
            db.session.commit()
            
            return {'message':'password change sucessful'}    
        else:
            raise HTTPException(status_code=401, detail = 'Passwords must be same and of length greater than 6 and must not be the same as old password ')
    else:
        raise HTTPException(status_code=401, detail = 'Please enter correct current password')




@app.post('/delete_user')
async def delete_user(my_id:int):
     db.session.query(ModelUser).filter_by(id = my_id).delete()
     db.session.commit()
     return {'message': 'deleted'}


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port = 8000)