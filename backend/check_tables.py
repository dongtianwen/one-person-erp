import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_tables():
    engine = create_async_engine('sqlite+aiosqlite:///./shubiao.db')
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = result.fetchall()
        print('Tables in database:')
        for t in tables:
            print(f'  - {t[0]}')

        print()
        print('Checking v1.11 tables:')
        v11_tables = ['datasets', 'dataset_versions', 'annotation_tasks', 'training_experiments', 'model_versions', 'delivery_packages']
        for t in v11_tables:
            try:
                result = await conn.execute(text(f'SELECT COUNT(*) FROM {t}'))
                count = result.scalar()
                print(f'  {t}: {count} rows')
            except Exception as e:
                print(f'  {t}: ERROR - {e}')

asyncio.run(check_tables())