import os
import sqlite3
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# ⚠️ ПАРОЛИ ⚠️
PASSWORD = "LukaSuperSecretChat2024!"  # Пароль для всех друзей
ADMIN_PASSWORD = "LukaBoss2024!"       # ТВОЙ СЕКРЕТНЫЙ ПАРОЛЬ
ADMIN_NICK = "Luka"                    # Твой зарезервированный ник

# --- БАЗА ДАННЫХ ---
DB_FILE = 'chat.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nick TEXT, emoji TEXT, text TEXT, is_admin INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nick, emoji, text, is_admin FROM messages ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "nick": r[1], "emoji": r[2], "text": r[3], "isAdmin": bool(r[4])} for r in rows]

def save_message(nick, emoji, text, is_admin):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages (nick, emoji, text, is_admin) VALUES (?, ?, ?, ?)", (nick, emoji, text, is_admin))
    conn.commit()
    msg_id = c.lastrowid
    conn.close()
    return msg_id

def delete_message(msg_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

def clear_all_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

init_db()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Секретный чат</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #eef2f5; margin: 0; padding: 10px; }
        #login-box, #chat-box { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        #chat-box { display: none; }
        
        #messages { height: 450px; overflow-y: scroll; border: 1px solid #e0e0e0; padding: 10px; margin-bottom: 10px; background: #f9f9f9; border-radius: 8px; display: flex; flex-direction: column; }
        .msg-row { display: flex; margin-bottom: 12px; width: 100%; align-items: flex-end; position: relative; }
        .msg-row.me { flex-direction: row-reverse; }
        
        .avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; color: white; margin: 0 10px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
        
        .msg-content { background: white; padding: 10px 14px; border-radius: 12px; max-width: 70%; display: flex; flex-direction: column; box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: relative; }
        .msg-row.me .msg-content { background: #dcf8c6; }
        
        /* СТИЛЬ ДЛЯ АДМИНА (КРАСНЫЙ) */
        .msg-row.admin .msg-content { background: #ff4d4d; border: 2px solid #cc0000; box-shadow: 0 3px 8px rgba(255, 77, 77, 0.4); }
        .msg-row.admin .nickname { color: #fff !important; text-shadow: 0 1px 2px rgba(0,0,0,0.3); }
        .msg-row.admin .text { color: #ffffff; font-weight: 500; }
        .msg-row.admin .avatar { border: 2px solid #cc0000; }

        .nickname { font-size: 12px; font-weight: bold; color: #555; margin-bottom: 4px; }
        .text { word-wrap: break-word; color: #222; font-size: 15px; }

        /* Кнопка удаления для админа */
        .delete-btn { position: absolute; top: -5px; right: -5px; background: red; color: white; border-radius: 50%; width: 20px; height: 20px; font-size: 10px; display: none; justify-content: center; align-items: center; cursor: pointer; border: none; padding: 0; }
        .msg-row.admin .delete-btn, .msg-row:hover .delete-btn { display: flex; }

        input[type="text"], input[type="password"] { width: 100%; box-sizing: border-box; padding: 12px; margin-bottom: 12px; border: 1px solid #ccc; border-radius: 8px; font-size: 15px; outline: none; }
        input:focus { border-color: #4CAF50; }
        button { padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; transition: 0.2s; }
        button:hover { background: #43a047; }
        
        .emojis { display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap; justify-content: center; }
        .emoji-btn { font-size: 24px; cursor: pointer; padding: 8px; border: 2px solid transparent; border-radius: 8px; background: #f0f0f0; width: 50px; height: 50px; display: flex; justify-content: center; align-items: center; transition: 0.2s; }
        .emoji-btn.selected { border-color: #4CAF50; background: #e8f5e9; transform: scale(1.1); }
    </style>
</head>
<body>
    <div id="login-box">
        <h2 style="text-align:center; color:#333;">Вход в чат</h2>
        <input type="text" id="nickname" placeholder="Твой никнейм">
        <p style="text-align:center; margin:5px 0 10px; color:#666;">Выбери аватарку:</p>
        <div class="emojis" id="emoji-container">
            <button class="emoji-btn" onclick="selectEmoji('🐺', this)">🐺</button>
            <button class="emoji-btn" onclick="selectEmoji('🦊', this)">🦊</button>
            <button class="emoji-btn" onclick="selectEmoji('🐻', this)">🐻</button>
            <button class="emoji-btn" onclick="selectEmoji('🐸', this)">🐸</button>
            <button class="emoji-btn" onclick="selectEmoji('🦁', this)">🦁</button>
            <button class="emoji-btn" onclick="selectEmoji('👽', this)">👽</button>
            <button class="emoji-btn" onclick="selectEmoji('👾', this)">👾</button>
            <button class="emoji-btn" onclick="selectEmoji('💀', this)">💀</button>
            <button class="emoji-btn" onclick="selectEmoji('☢️', this)">☢️</button>
            <button class="emoji-btn" onclick="selectEmoji('🥷', this)">🥷</button>
            <button class="emoji-btn" onclick="selectEmoji('💻', this)">💻</button>
            <button class="emoji-btn" onclick="selectEmoji('🎭', this)">🎭</button>
        </div>
        <input type="password" id="password" placeholder="Пароль">
        <button onclick="login()">Войти</button>
        <p id="error" style="color:red; text-align:center; font-weight:bold; margin-bottom: 0;"></p>
    </div>

    <div id="chat-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h2 style="margin: 0; color:#333;">Общий чат</h2>
            <div>
                <button id="clear-btn" onclick="clearChat()" style="width: auto; padding: 8px 15px; background: #f39c12; font-size: 14px; display: none; margin-right: 5px;">Очистить</button>
                <button onclick="logout()" style="width: auto; padding: 8px 15px; background: #e74c3c; font-size: 14px;">Выйти</button>
            </div>
        </div>
        <div id="messages"></div>
        <div style="display:flex; gap:10px;">
            <input type="text" id="message" placeholder="Написать сообщение..." onkeypress="if(event.key === 'Enter') sendMessage()" style="margin-bottom:0;">
            <button onclick="sendMessage()" style="width: 120px;">Отправить</button>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        var socket = io();
        var currentNick = "";
        var currentEmoji = "🐺"; 
        var myId = Math.random().toString(36).substr(2, 9); 
        var isAdmin = false;
        
        function selectEmoji(emoji, btn) {
            currentEmoji = emoji;
            document.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        }
        document.querySelector('.emoji-btn').classList.add('selected');

        function addMessageToScreen(data) {
            var messages = document.getElementById('messages');
            
            var row = document.createElement('div');
            row.className = 'msg-row';
            row.id = "msg-" + data.id; // Уникальный ID для удаления
            if (data.isAdmin) row.classList.add('admin');
            
            var avatar = document.createElement('div');
            avatar.className = 'avatar';
            avatar.innerText = data.emoji;
            
            var hash = 0;
            for (var i = 0; i < data.nick.length; i++) hash = data.nick.charCodeAt(i) + ((hash << 5) - hash);
            var color = 'hsl(' + (hash % 360) + ', 70%, 50%)'; 
            if (!data.isAdmin) avatar.style.backgroundColor = color;

            var content = document.createElement('div');
            content.className = 'msg-content';
            
            var nickDiv = document.createElement('div');
            nickDiv.className = 'nickname';
            nickDiv.innerText = data.isAdmin ? data.nick + " 🧙‍♂️" : data.nick;
            if (!data.isAdmin) nickDiv.style.color = color;
            
            var textDiv = document.createElement('div');
            textDiv.className = 'text';
            textDiv.innerText = data.text;

            // Кнопка удаления (показываем только если админ)
            if (isAdmin) {
                var delBtn = document.createElement('button');
                delBtn.className = 'delete-btn';
                delBtn.innerText = '✕';
                delBtn.onclick = function() { socket.emit('delete_message', data.id); };
                content.appendChild(delBtn);
            }
            
            content.appendChild(nickDiv);
            content.appendChild(textDiv);
            
            row.appendChild(avatar);
            row.appendChild(content);
            messages.appendChild(row);
            messages.scrollTop = messages.scrollHeight;
        }

        function login() {
            var pwd = document.getElementById('password').value;
            var nick = document.getElementById('nickname').value.trim();
            
            if (pwd === "{{ admin_password }}") {
                currentNick = "{{ admin_nick }}";
                isAdmin = true;
            } else if (pwd === "{{ password }}") {
                if (nick.toLowerCase() === "{{ admin_nick }}".toLowerCase()) {
                    document.getElementById('error').innerText = "Этот ник зарезервирован создателем!";
                    return;
                }
                if (nick === "") {
                    document.getElementById('error').innerText = "Введи никнейм!";
                    return;
                }
                currentNick = nick;
                isAdmin = false;
            } else {
                document.getElementById('error').innerText = "Неверный пароль!";
                return;
            }

            document.getElementById('login-box').style.display = 'none';
            document.getElementById('chat-box').style.display = 'block';
            document.getElementById('message').focus();
            
            if (isAdmin) document.getElementById('clear-btn').style.display = 'inline-block';
            
            // Запрашиваем историю
            socket.emit('get_history');
        }

        function logout() {
            document.getElementById('chat-box').style.display = 'none';
            document.getElementById('login-box').style.display = 'block';
            document.getElementById('password').value = "";
            document.getElementById('error').innerText = "";
            document.getElementById('nickname').value = "";
            isAdmin = false;
            document.getElementById('clear-btn').style.display = 'none';
            document.getElementById('messages').innerHTML = "";
        }

        function sendMessage() {
            var input = document.getElementById('message');
            var text = input.value;
            if(text.trim() !== "") {
                socket.emit('send_message', {
                    'text': text,
                    'nick': currentNick,
                    'emoji': isAdmin ? '👑' : currentEmoji,
                    'isAdmin': isAdmin
                });
                input.value = "";
            }
        }

        function clearChat() {
            if (isAdmin) socket.emit('clear_chat');
        }

        socket.on('history', function(messages) {
            document.getElementById('messages').innerHTML = "";
            messages.forEach(addMessageToScreen);
        });

        socket.on('receive_message', function(data) {
            if (data.id) addMessageToScreen(data);
        });

        socket.on('message_deleted', function(msg_id) {
            var el = document.getElementById("msg-" + msg_id);
            if (el) el.remove();
        });

        socket.on('chat_cleared', function() {
            document.getElementById('messages').innerHTML = "";
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, password=PASSWORD, admin_password=ADMIN_PASSWORD, admin_nick=ADMIN_NICK)

@socketio.on('get_history')
def handle_get_history():
    emit('history', get_messages())

@socketio.on('send_message')
def handle_message(data):
    msg_id = save_message(data['nick'], data['emoji'], data['text'], 1 if data['isAdmin'] else 0)
    data['id'] = msg_id
    emit('receive_message', data, broadcast=True)

@socketio.on('delete_message')
def handle_delete(data):
    # В реальном проекте здесь нужно проверять пароль, но для простоты доверяем клиенту
    delete_message(data)
    emit('message_deleted', data, broadcast=True)

@socketio.on('clear_chat')
def handle_clear():
    clear_all_messages()
    emit('chat_cleared', broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
