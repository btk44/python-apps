from fastapi import FastAPI
from apps.expenses import expenses_router

app = FastAPI()
app.include_router(expenses_router)



