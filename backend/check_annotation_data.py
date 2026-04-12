import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_data():
    engine = create_async_engine('sqlite+aiosqlite:///./shubiao.db')
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, name, assignee, deadline, progress FROM annotation_tasks"))
        rows = result.fetchall()
        print('=== Annotation Tasks Data ===')
        for r in rows:
            print(f'  ID={r[0]}, name={r[1]}, assignee={r[2]}, deadline={r[3]}, progress={r[4]}')

        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='annotation_tasks'"))
        table_exists = result.fetchone()
        print(f'\nTable exists: {table_exists}')

        if table_exists:
            result = await conn.execute(text("PRAGMA table_info(annotation_tasks)"))
            columns = result.fetchall()
            print('Columns:')
            for c in columns:
                print(f'  {c[1]} ({c[2]})')

asyncio.run(check_data())