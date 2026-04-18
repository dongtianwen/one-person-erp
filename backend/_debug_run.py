import asyncio, sys
sys.path.insert(0, ".")

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from app.core.agent_rules import evaluate_overdue_payments, run_business_decision_rules

    engine = create_async_engine("sqlite+aiosqlite:///./shubiao.db")
    async with AsyncSession(engine) as db:
        print("Testing evaluate_overdue_payments...")
        try:
            result = await evaluate_overdue_payments(db)
            print(f"  Result: {len(result)} suggestions")
            for s in result:
                print(f"    title={s['title'][:60]}")
        except Exception as e:
            print(f"  ERROR: {e}")

        print("\nTesting run_business_decision_rules...")
        try:
            all_s = await run_business_decision_rules(db)
            print(f"  Result: {len(all_s)} suggestions")
            for s in all_s:
                print(f"    type={s['suggestion_type']} title={s['title'][:60]}")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    await engine.dispose()

asyncio.run(main())
