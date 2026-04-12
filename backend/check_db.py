import sqlite3

conn = sqlite3.connect('shubiao.db')
cur = conn.cursor()

# 获取所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:')
for t in tables:
    print(f'  {t[0]}')

# 检查 annotation_tasks 表结构
print('\nannotation_tasks columns:')
cur.execute("PRAGMA table_info(annotation_tasks)")
cols = cur.fetchall()
for col in cols:
    print(f'  {col[1]} ({col[2]})')

# 检查是否有数据
cur.execute("SELECT COUNT(*) FROM annotation_tasks")
count = cur.fetchone()[0]
print(f'\nannotation_tasks row count: {count}')

# 检查 training_experiments 表
print('\ntraining_experiments columns:')
cur.execute("PRAGMA table_info(training_experiments)")
cols = cur.fetchall()
for col in cols:
    print(f'  {col[1]} ({col[2]})')

# 检查 model_versions 表
print('\nmodel_versions columns:')
cur.execute("PRAGMA table_info(model_versions)")
cols = cur.fetchall()
for col in cols:
    print(f'  {col[1]} ({col[2]})')

conn.close()
