from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)

def load_premium():
    if os.path.exists('premium.json'):
        with open('premium.json', 'r') as f:
            return json.load(f)
    return {"premium_guilds": []}

def save_premium(data):
    with open('premium.json', 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    data = load_premium()
    return render_template('index.html', guilds=data['premium_guilds'])

@app.route('/add', methods=['POST'])
def add():
    guild_id = request.form.get('guild_id')
    data = load_premium()
    if guild_id and guild_id not in data['premium_guilds']:
        data['premium_guilds'].append(guild_id)
        save_premium(data)
    return redirect(url_for('index'))

@app.route('/remove/<guild_id>')
def remove(guild_id):
    data = load_premium()
    if guild_id in data['premium_guilds']:
        data['premium_guilds'].remove(guild_id)
        save_premium(data)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)