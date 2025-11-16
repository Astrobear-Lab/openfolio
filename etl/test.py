import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:Js58195138~@db.xgfbjjqhcscinwziomkd.supabase.co:5432/postgres')
    print('✅ 연결 성공!')
    conn.close()
except Exception as e:
    print('❌ 연결 실패:', e)