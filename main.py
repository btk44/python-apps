# from fastapi import FastAPI
# from apps.expensesenses import expenses_router

# app = FastAPI()
# app.include_router(expenses_router)


from apps.expenses.main import app  # Import the FastAPI app from the main module
