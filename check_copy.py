import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://agents:mongo_secret_2026@localhost:4717/ai_agents?authSource=admin")
    db = client["ai_agents"]
    async for copy in db["budget_copies"].find({}, {"_id": 0}):
        print(f"\n=== Copy: {copy.get('name')} (source: {copy.get('source_month')}) ===")
        for e in copy.get("entries", []):
            if e.get("type") == "income":
                print(f"  Income: {e.get('name')} amount={e.get('amount')} amount_max={e.get('amount_max')}")
        for e in copy.get("entries", []):
            if e.get("source") == "loan":
                print(f"  Loan entry: {e.get('name')} amount={e.get('amount')}")
        loans = copy.get("loans", [])
        print(f"  Loans array: {len(loans)}")
        for l in loans:
            print(f"    Loan: {l.get('bank')} monthly={l.get('monthly_payment')}")
    client.close()

asyncio.run(main())
