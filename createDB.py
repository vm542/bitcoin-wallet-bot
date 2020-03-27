import sqlite3

conn = sqlite3.connect("wallets.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE wallets
                (user_id text, public_address text, private_key text)
                """)