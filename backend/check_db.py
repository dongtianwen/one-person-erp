import sqlite3
import json
conn = sqlite3.connect('shubiao.db')
cur = conn.cursor()

cur.execute("SELECT id, decision_type, suggestion_type, title, description, priority, status, suggested_action, risk_score FROM agent_suggestions LIMIT 10")
rows = cur.fetchall()
result = []
for r in rows:
    result.append({
        "id": r[0],
        "decision_type": r[1],
        "suggestion_type": r[2],
        "title": r[3],
        "description": r[4],
        "priority": r[5],
        "status": r[6],
        "suggested_action": r[7],
        "risk_score": r[8]
    })
with open('suggestions.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("Done")
conn.close()
