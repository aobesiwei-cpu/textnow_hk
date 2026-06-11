from tn_db import get_db_dict
import pymysql

conn = get_db_dict()
cur = conn.cursor(pymysql.cursors.DictCursor)

# 测试修复后的 conversations 查询
try:
    sql = """
        SELECT c.*,
               (SELECT content FROM messages WHERE conversation_id=c.id ORDER BY sent_time DESC LIMIT 1) as last_preview,
               (SELECT DATE_FORMAT(sent_time,'%%Y-%%m-%%d %%H:%%i') FROM messages WHERE conversation_id=c.id ORDER BY sent_time DESC LIMIT 1) as last_time_str,
               (SELECT COUNT(*) FROM messages WHERE conversation_id=c.id AND direction=1 AND read_status=0) as unread_count,
               (SELECT COUNT(*) FROM messages WHERE conversation_id=c.id) as msg_count,
               a.phone as account_phone, a.email as account_email
        FROM conversations c
        LEFT JOIN accounts a ON c.account_id=a.id
        ORDER BY c.last_message_time DESC LIMIT 200
    """
    cur.execute(sql)
    rows = cur.fetchall()
    print(f"SUCCESS - {len(rows)} conversations")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

conn.close()
