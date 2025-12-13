from flask import Flask
from threading import Thread
import time

app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Альтернативный вариант с ping
def ping_server():
    import requests
    while True:
        try:
            # Ping ваш же Replit
            requests.get("https://ваш-проект.ваш-юзер.repl.co")
            print("Ping отправлен")
        except:
            pass
        time.sleep(300)  # Каждые 5 минут
