from pydantic import BaseModel, HttpUrl

class CreateRequest(BaseModel):
    url: HttpUrl

class CreateResponse(BaseModel):
    short_code: str
    short_url: str