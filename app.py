import os
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# ⚠️ ТВОЙ ПАРОЛЬ ⚠️
PASSWORD = "12345" 

# HTML-шаблон чата (встроен прямо сюда для удобства)
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Секретный чат</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; background: #f0f2f5; margin: 0; padding: 20px; }
        #login-box, #chat-box { max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        #chat-box { display: none; }
        #messages { height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; background: #e5ddd5; border-radius: 5px; }
        .msg { background: white; padding: 8px; margin-bottom: 5px; border-radius: 5px; width: fit-content; max-width: 80%; }
        .msg.me { background: #dcf8c6; margin-left: auto; }
        input[type="text"], input[type="password"] { width: 80%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 5px; }
        button { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #45a049; }
    </style>
</head>
<body>
    <div id="login-box">
        <h2>Вход в чат</h2>
        <p>Введите пароль:</p>
        <input type="password" id="password" placeholder="Пароль">
        <button onclick="login()">Войти</button>
        <p id="error" style="color:red;"></p>
    </div>

    <div id="chat-box">
        <h2>Общий чат</h2>
        <div id="messages"></div>
        <input type="text" id="message" placeholder="Сообщение...">
        <button onclick="sendMessage()">Отправить</button>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        var socket = io();
        
        function login() {
            var pwd = document.getElementById('password').value;
            if(pwd === "{{ password }}") {
                document.getElementById('login-box').style.display = 'none';
                document.getElementById('chat-box').style.display = 'block';
            } else {
                document.getElementById('error').innerText = "Неверный пароль!";
            }
        }

        function sendMessage() {
            var input = document.getElementById('message');
            var text = input.value;
            if(text.trim() !== "") {
                socket.emit('send_message', {'text': text});
                input.value = "";
            }
        }

        document.getElementById('message').addEventListener('keypress', function (e) {
            if (e.key === 'Enter') sendMessage();
        });

        socket.on('receive_message', function(data) {
            var messages = document.getElementById('messages');
            var div = document.createElement('div');
            div.className = 'msg';
            div.innerText = data.text;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, password=PASSWORD)

@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)