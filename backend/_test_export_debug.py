import asyncio
import traceback
from app.database import async_session
from app.crud.rd_expense import rd_expense
from app.core.rd_expense_utils import write_rd_expense_excel

async def test():
    try:
        async with async_session() as db:
            items, _ = await rd_expense.get_multi(db, skip=0, limit=5)
            print(f"items: {len(items)}")

            # Call the actual function with full traceback
            print("Calling write_rd_expense_excel...")
            try:
                buf = await write_rd_expense_excel(db, items)
                print(f"buf type: {type(buf)}")
                print(f"buf value: {buf}")
                if buf is not None:
                    print(f"buf size: {len(buf.getvalue())}")
                else:
                    print("BUG: function returned None!")
                    # Inspect the function source
                    import inspect
                    src = inspect.getsource(write_rd_expense_excel)
                    print("Function source last 10 lines:")
                    lines = src.split('\n')
                    for line in lines[-10:]:
                        print(f"  {line}")
            except Exception as e:
                print(f"write_rd_expense_excel ERROR: {e}")
                traceback.print_exc()

    except Exception as e:
        print(f"OUTER ERROR: {e}")
        traceback.print_exc()

asyncio.run(test())
