from datetime import datetime
import json
import logging
from pyexpat.errors import messages
from apps.expenses.constants import AZURE_API_KEY, AZURE_API_VERSION, AZURE_OPENAI_ENDPOINT
from apps.expenses.database.models.category import Category
from apps.expenses.database.models.transaction import Transaction
from . import router
from sqlalchemy import select, and_
from ..database.models.account import Account
from ..database.session import SessionLocal
from pydantic import BaseModel
from fastapi import HTTPException, status
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION
)

class TransactionPromptCommand(BaseModel):
    processingUserId: int = 1
    prompt: str

class TransactionDto(BaseModel):
    id: int
    ownerId: int
    amount: float
    categoryId: int
    accountId: int
    date: datetime
    comment: str | None = None
    active: bool

class DatabaseInformation:
    accounts: list[Account]
    categories: list[Category]

async def get_all_accounts_and_categories(owner_id: int) -> str:
    async with SessionLocal() as session:
        accounts_result = await session.scalars(select(Account).where(and_(Account.owner_id == owner_id, Account.active == True)))
        accounts = accounts_result.all()
        categories_result = await session.scalars(select(Category).where(and_(Category.owner_id == owner_id, Category.active == True)))
        categories = categories_result.all()

        accounts_data_string = "\n".join([f"{a.id}: {a.name} (code: {a.unique_code}, currency: {a.currency_id})" for a in accounts])
        categories_data_string = "\n".join([f"{c.id}: {c.name} (code: {c.unique_code}, parent_id: {c.parent_id})" for c in categories])

        return f"Accounts:\n{accounts_data_string}\nCategories:\n{categories_data_string}"

@router.post("/transaction/trycreate", status_code=status.HTTP_200_OK)
async def process_transactions(command: TransactionPromptCommand):
    messages = [
        {"role": "system", "content": "You will receive a description of a transaction that a user wants to create. "
                                      "Your task is to extract the relevant information from the description and respond with a line of text containing the key details of the transaction. "
                                      "You have access to a tool that allows you to query the database for all accounts and categories of the user. "
                                      f"If no date is provided in the description, use the current date. Today is {datetime.now().date()}."
                                      "Use this tool to get the necessary information to create the transaction. Use owner_id = 1 for all queries. "
                                      "The response text should look like this: 'Date: 2024-05-25, Amount: 25.6, Category Name: auto, Account Name: Alior PLN (B), Comment: zakupy spożywcze'. "
                                      " If you need to ask the user for more information, do so."},
        {"role": "user", "content": command.prompt}
    ]

    tools = [
    {
        "type": "function",
        "function": {
            "name": "get_all_accounts_and_categories",
            "description": "Queries the database to retrieve all accounts and categories for a given user. This information can be used to create transactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner_id": {
                        "type": "integer",
                        "description": "The ID of the user for whom to retrieve accounts and categories"
                    }
                },
                "required": ["owner_id"]
            }
        }
    }]

    while True:
        response = client.chat.completions.create(
            model="o4-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        #Model wants to call a tool
        if msg.tool_calls:
            messages.append(msg)
            for tool_call in msg.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = await get_all_accounts_and_categories(**args)  # dispatch to your function
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        else:
            # Model gave a final answer
            return {"response": msg.content}
        
        
@router.post("/transaction/trycreate2", status_code=status.HTTP_200_OK)
async def process_transactions(command: TransactionPromptCommand):
    messages = [
        {"role": "system", "content": "You will receive a description of a transaction that a user wants to create. "
                                      "Your task is to extract the relevant information from the description and respond with a line of text containing the key details of the transaction. "
                                      "You have a list of accounts and categories of the user. Use this information to create the transaction. "
                                      f"{await get_all_accounts_and_categories(owner_id=1)}. "
                                      f"If no date is provided in the description, use the current date. Today is {datetime.now().date()}."
                                      "The response text should look like this: 'Date: 2024-05-25, Amount: 25.6, Category Name: auto, Account Name: Alior PLN (B), Comment: zakupy spożywcze'. "
                                      " If you need to ask the user for more information, do so."},
        {"role": "user", "content": command.prompt}
    ]

    while True:
        response = client.chat.completions.create(
            model="o4-mini",
            messages=messages
        )

        msg = response.choices[0].message

        return {"response": msg.content}