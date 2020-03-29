import telebot
import sqlite3
import threading
from bit import Key
from telebot import types
from bit.network import satoshi_to_currency
from hashlib import sha256

lock = threading.Lock()

bottoken = ""
bot = telebot.TeleBot(bottoken)

conn = sqlite3.connect("wallets.db", check_same_thread=False)
cursor = conn.cursor()
current_wallet = (-1, -1)

markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
markup.add('💰 Solde', '↔️ Retirer')

markup2 = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
markup2.add('↔️ Retirer')

markup3 = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
markup3.add('Annuler')

destinataire = ''
somme = 0

digits58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
 
def decode_base58(bc, length):
    n = 0
    for char in bc:
        n = n * 58 + digits58.index(char)
    return n.to_bytes(length, 'big')

def check_address(bc):
    try:
        bcbytes = decode_base58(bc, 25)
        return bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]
    except Exception:
        return False

def wallet_exist(user_id):
    conn = sqlite3.connect("wallets.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wallets WHERE user_id=?', (str(user_id),))
    row = cursor.fetchall()
    if (len(row) == 0):
        return 0
    global current_wallet 
    current_wallet = (row[0][1], row[0][2])
    return 1

def create_wallet(user_id):    
    public_address = Key()
    private_key = public_address.to_wif()
    cursor.execute("INSERT INTO wallets (user_id, public_address, private_key) values (?, ?, ?)",
            (str(user_id), str(public_address.address), str(private_key)))
    conn.commit()
    global current_wallet 
    current_wallet = (str(public_address.address), str(private_key))

@bot.message_handler(commands=['start'])
def repeat_all_messages(message):
    global current_wallet
    user_id = message.from_user.id
    if wallet_exist(user_id):
        public_address = str(current_wallet[0])
        msg = bot.send_message(message.chat.id, "Bonjour, voici l'adresse de votre wallet Bitcoin : \n\n```" + public_address + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
    else:
        create_wallet(user_id)
        public_address = str(current_wallet[0])
        msg = bot.send_message(message.chat.id, "Bonjour, j'ai créé pour vous un wallet Bitcoin, voici son son adresse : \n\n```" + public_address + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_step)

def process_step(message):
    chat_id = message.chat.id
    public_address = current_wallet[0]
    private_key = current_wallet[1]
    key = Key(private_key)
    solde = int(key.get_balance('btc'))
    if message.text=='💰 Solde':
        msg = bot.send_message(message.chat.id, "Adresse de votre wallet Bitcoin : ```" + str(public_address) + "```\n\nVous avez " + str(solde) + " BTC (~" + str(satoshi_to_currency(int(solde) * 100000000, 'eur')) + " EUR).", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_step)
    elif message.text == '↔️ Retirer':
        msg = bot.send_message(message.chat.id, "Entrez l'adresse du destinataire", reply_markup=markup3, parse_mode="Markdown")
        bot.register_next_step_handler(msg, get_address)

def get_address(message):
    public_address = current_wallet[0]
    private_key = current_wallet[1]
    key = Key(private_key)
    solde = int(key.get_balance('btc'))
    if message.text=='Annuler':
        msg = bot.send_message(message.chat.id, "Bonjour, voici l'adresse de votre wallet Bitcoin : \n\n```" + public_address + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_step)
    else:
        global destinataire
        destinataire = str(message.text)
        if (check_address(destinataire) == False):
            msg = bot.send_message(message.chat.id, "L'adresse du destinataire est incorrecte !", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_step)
        else:
            msg = bot.send_message(message.chat.id, "Quelle somme voulez-vous envoyer ?\n\nFonds disponibles : " + str(solde) + " BTC (~" + str(satoshi_to_currency(int(solde) * 100000000, 'eur')) + " EUR).", reply_markup=markup3, parse_mode="Markdown")
            bot.register_next_step_handler(msg, get_somme)

def get_somme(message):
    public_address = current_wallet[0]
    private_key = current_wallet[1]
    key = Key(private_key)
    if message.text=='Annuler':
        msg = bot.send_message(message.chat.id, "Bonjour, voici l'adresse de votre wallet Bitcoin : \n\n```" + public_address + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_step)
    else:
        try:
            somme = float(message.text)
            try:
                outputs = [(str(destinataire), int(somme), 'btc'),]
                trans_link = key.send(outputs)
                bot.send_message(message.chat.id, "Très bien, l'argent a été envoyé ! Voici l'adresse de votre transaction " + str(trans_link) + ".", reply_markup=markup, parse_mode="Markdown")
            except:
                msg = bot.send_message(message.chat.id, "Vos BTC n'ont pas été envoyés ! Vérifiez bien que vous avez assez de fonds et réessayez.", reply_markup=markup, parse_mode="Markdown")
                bot.register_next_step_handler(msg, process_step)
        except:
            msg = bot.send_message(message.chat.id, "Entrez la somme à envoyer sous le format suivant : *0.843* (avec un point) !", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_step)

if  __name__ == '__main__':
    bot.polling(none_stop=True)