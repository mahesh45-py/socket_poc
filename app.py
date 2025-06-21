from flask import Flask, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import eventlet
from collections import defaultdict

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drawings.db'
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class DrawingEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'start', 'draw', 'end'

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

active_users = {}

@socketio.on('join')
def handle_join(data):
    username = data.get('username', 'Anonymous')
    sid = request.sid
    active_users[sid] = username
    emit('user_list', list(active_users.values()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in active_users:
        del active_users[sid]
        emit('user_list', list(active_users.values()), broadcast=True)

@socketio.on('draw_event')
def handle_draw_event(data):
    # Save to DB
    event = DrawingEvent(x=data['x'], y=data['y'], type=data['type'])
    db.session.add(event)
    db.session.commit()
    # Broadcast to all clients
    emit('draw_event', data, broadcast=True)

@socketio.on('get_history')
def handle_get_history():
    events = DrawingEvent.query.all()
    history = [{'x': e.x, 'y': e.y, 'type': e.type} for e in events]
    emit('history', history)

@socketio.on('clear_board')
def handle_clear_board():
    # Clear the database
    DrawingEvent.query.delete()
    db.session.commit()
    # Notify all clients to clear their boards
    emit('clear_board', broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
