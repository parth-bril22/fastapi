# build a schema using pydantic
from pydantic import BaseModel

class User(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    # register_time: datetime
    

    class Config:
        orm_mode = True

class LoginSchema(BaseModel):
    email : str
    password : str

    class Config:
        orm_mode = True
    
class PasswordResetSchema(BaseModel):
    password: str
    confirm_password : str

    class Config:
        orm_mode = True

class PasswordChangeSchema(BaseModel):
    current_password: str
    new_password: str
    confirm_password : str

    class Config:
        orm_mode = True

class EmailSchema(BaseModel):
    email:str

    class Config:
        orm_mode = True


#!-------------------------------!!!!!!------------------------------

# build a schema using pydantic
from typing import Dict, Optional
from pydantic import BaseModel


class NodeSchema(BaseModel):
    _id: int #id is made private by the "_" before its name, so frontend need not enter it.
    _name: str = "name"
    _path: str = "path"
    type: str = "chat"
    node_type: str = "start_node"
    position: Dict = {"top":"0","left":"0"}

    # all fields from all types are present. Later in api.py, only the relevant fields will be taken into consideration
    properties: Dict = {"text":"","value":"" ,"name" :"", "type":"", "source":"", "message":"", "btn":"", "id":"" }

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True


class ConnectionSchema(BaseModel):
    _id: int
    _name: Optional[str]
    sub_node: str = ""
    source_node: str = ""
    target_node: str = ""

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True
    


class NodeTypeSchema(BaseModel):
    _id: int
    type: str
    properties: Dict

    class Config:
        orm_mode = True
        underscore_attrs_are_private = True

class CustomFieldSchema(BaseModel):
    _id: int
    name: str = ""
    type: str = ""
    value: str = ""

    class Config:
        orm_mode = True


