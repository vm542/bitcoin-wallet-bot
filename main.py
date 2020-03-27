import telebot
import sqlite3
from bit import Key
import threading

lock = threading.Lock()

bottoken = ""
bot = telebot.TeleBot(bottoken)

conn = sqlite3.connect("wallets.db", check_same_thread=False)
cursor = conn.cursor()
current_wallet = (-1, -1)

def wallet_exist(user_id):
    conn = sqlite3.connect("wallets.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wallets WHERE user_id=?', (str(user_id),))
    row = cursor.fetchall()
    if (len(row) == 0):
        return 0
    current_wallet = (row[0][1], row[0][2])
    print(current_wallet)
    return 1

def create_wallet(user_id):    
    public_address = Key()
    private_key = public_address.to_wif()
    cursor.execute("INSERT INTO wallets (user_id, public_address, private_key) values (?, ?, ?)",
            (str(user_id), str(public_address.address), str(private_key)))
    conn.commit()

@bot.message_handler(commands=['start'])
def repeat_all_messages(message):
    user_id = message.from_user.id
    if wallet_exist(user_id):
        bot.send_message(message.chat.id, "Vous avez déjà un wallet !")
    else:
        create_wallet(user_id)
        bot.send_message(message.chat.id, "Parfait, le wallet a été crée !")

if  __name__ == '__main__':
    bot.polling(none_stop=True)