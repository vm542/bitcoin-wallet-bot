import telebot
import sqlite3
import threading
from bit import Key
from telebot import types
from bit.network import satoshi_to_currency
from hashlib import sha256
import decimal
from bit.network import get_fee, get_fee_cached

lock = threading.Lock()

bottoken = "" #your bot's token (created with @botfather)
bot = telebot.TeleBot(bottoken)

#connection to the sqlite database

conn = sqlite3.connect("wallets.db", check_same_thread=False)
cursor = conn.cursor()

#declaration of the keyboards

markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
markup.add('💰 Solde', '↔️ Retirer')

markup2 = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
markup2.add('↔️ Retirer')

markup3 = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
markup3.add('Annuler')

digits58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
 
def decode_base58(bc, length):
    n = 0
    for char in bc:
        n = n * 58 + digits58.index(char)
    return n.to_bytes(length, 'big')

#check if the bitcoin address is correct

def check_address(bc):
    try:
        bcbytes = decode_base58(bc, 25)
        return bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]
    except Exception:
        return False

#check if the user has already created a wallet

def wallet_exist(user_id):
    conn = sqlite3.connect("wallets.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wallets WHERE user_id=?', (str(user_id),))
    row = cursor.fetchall()
    if (len(row) == 0):
        return 0 #no occurences in the database
    #global current_address, current_privkey
    #current_address = row[0][1]
    #current_privkey = row[0][2]
    return (row[0][1], row[0][2])

#create a wallet and save it in the database

def create_wallet(user_id):
    key = Key()
    current_address = key.address
    current_privkey = key.to_wif()
    cursor.execute("INSERT INTO wallets (user_id, public_address, private_key) values (?, ?, ?)",
            (str(user_id), str(current_address), str(current_privkey)))
    conn.commit()

@bot.message_handler(commands=['stats'])
def main(message):
    conn = sqlite3.connect("wallets.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wallets')
    row = cursor.fetchall()
    bot.send_message(message.chat.id, len(row), parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def main(message):
    current_user_id = message.from_user.id
    current_wallet = wallet_exist(current_user_id)
    if wallet_exist(current_user_id) != 0:
        msg = bot.send_message(message.chat.id, "Bonjour, voici l'adresse de votre wallet Bitcoin : \n\n```" + str(current_wallet[0]) + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
    else:
        create_wallet(current_user_id)
        current_wallet = wallet_exist(current_user_id)
        msg = bot.send_message(message.chat.id, "Bonjour, j'ai créé pour vous un wallet Bitcoin, voici son son adresse : \n\n```" + str(current_wallet[0]) + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_step)

def process_step(message):
    current_user_id = message.from_user.id
    current_wallet = wallet_exist(current_user_id)
    current_key = Key(current_wallet[1])
    solde = decimal.Decimal(current_key.get_balance('btc'))
    if message.text=='💰 Solde':
        msg = bot.send_message(message.chat.id, "Adresse de votre wallet Bitcoin : ```" + current_wallet[0] + "```\n\nVous avez " + str(solde) + " BTC (~" + str(satoshi_to_currency(decimal.Decimal(solde) * decimal.Decimal(100000000), 'eur')) + " EUR).", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_step)
    elif message.text == '↔️ Retirer':
        msg = bot.send_message(message.chat.id, "Entrez l'adresse du destinataire", reply_markup=markup3, parse_mode="Markdown")
        bot.register_next_step_handler(msg, get_address)

def get_address(message):
    current_user_id = message.from_user.id
    current_wallet = wallet_exist(current_user_id)
    current_key = Key(current_wallet[1])
    solde = decimal.Decimal(current_key.get_balance('btc'))
    global destinataire
    if message.text=='Annuler':
        msg = bot.send_message(message.chat.id, "Bonjour, voici l'adresse de votre wallet Bitcoin : \n\n```" + current_wallet[0] + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_step)
    else:
        destinataire = str(message.text)
        if (check_address(destinataire) == False):
            msg = bot.send_message(message.chat.id, "L'adresse du destinataire est incorrecte !", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_step)
        else:
            msg = bot.send_message(message.chat.id, "Quelle somme voulez-vous envoyer ?\n\nFonds disponibles : " + str(solde) + " BTC (~" + str(satoshi_to_currency(decimal.Decimal(solde) * decimal.Decimal(100000000), 'eur')) + " EUR).", reply_markup=markup3, parse_mode="Markdown")
            bot.register_next_step_handler(msg, lambda msg: get_somme(msg, destinataire))

def get_somme(message, destinataire):
    current_user_id = message.from_user.id
    current_wallet = wallet_exist(current_user_id)
    current_key = Key(current_wallet[1])
    solde = decimal.Decimal(current_key.get_balance('btc'))
    if message.text=='Annuler':
        msg = bot.send_message(message.chat.id, "Bonjour, voici l'adresse de votre wallet Bitcoin : \n\n```" + current_wallet[0] + "```\n\nUtilisez-la pour réapprovisionner votre porte-feuille Bitcoin.", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_step)
    else:
        try:
            somme = float(message.text)
            try:
                outputs = [(str(destinataire), float(somme), 'btc'),]
                trans_link = current_key.send(outputs)
                msg = bot.send_message(message.chat.id, "Très bien, l'argent a été envoyé ! Voici l'adresse de votre transaction :\nhttps://blockchain.info/tx/" + str(trans_link) + ".", reply_markup=markup, parse_mode="Markdown")
                bot.register_next_step_handler(msg, process_step)
            except:
                msg = bot.send_message(message.chat.id, "Vos BTC n'ont pas été envoyés ! Vérifiez bien que vous avez assez de fonds et réessayez.", reply_markup=markup, parse_mode="Markdown")
                bot.register_next_step_handler(msg, process_step)
        except:
            msg = bot.send_message(message.chat.id, "Entrez la somme à envoyer sous le format suivant : *0.843* (avec un point) !", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_step)

if  __name__ == '__main__':
    bot.polling(none_stop=True)