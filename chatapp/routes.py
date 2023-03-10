from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_user, current_user, login_required, logout_user
from flask_socketio import send, join_room, leave_room, emit

from chatapp import app, db, socketio, ROOMS
import bcrypt
from chatapp.models import User

active_users = {
}

ROOMS = []
user_room = str()


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        passw = request.form.get('pass')
        user = User.query.filter_by(username=username).first()
        if user:
            if bcrypt.checkpw(passw.encode('utf-8'), user.password):
                flash("Logged In", category='success')
                login_user(user, remember=True)
                return redirect(url_for('enter_code'))
            else:
                flash("Wrong Details. Please Try Again!", category='error')
        else:
            flash('User does not exists! Please Sign up!', category='error')
    return render_template('login.html', user=current_user)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        passw = request.form.get('pass')
        if len(passw) < 8: 
            flash('Password must be alteast 8 characters.', category='error');
        else:
            hashed_password = bcrypt.hashpw(passw.encode('utf-8'), bcrypt.gensalt())
            if email and username and passw:
                user = User(email=email, username = username, password=hashed_password)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash("User Created", category='success')
            return redirect(url_for('enter_code'))
    return render_template('signup.html', user=current_user)


@app.route('/code', methods=['POST', 'GET'])
@login_required
def enter_code():
    if request.method == 'POST':
        user_room = request.form.get('code')
        if not len(user_room) == 6:
            flash('Code should be of 6 Characters only.', category='error')
        else:
            session['user_room'] = user_room
            if user_room not in ROOMS:
                ROOMS.append(user_room)
                active_users[user_room] = []
            return redirect(url_for('thechatapp'))
    return render_template('code.html', user=current_user)


@app.route('/leaveroom')
@login_required
def leaveroom():
    return redirect(url_for('enter_code'))


@app.route('/thechatapp')
@login_required
def thechatapp():
    user_room = session['user_room']
    return render_template('chatapp.html', user=current_user, username = current_user.username, user_room = user_room)


@app.route('/mydetails', methods=['POST', 'GET'])
@login_required
def mydetails():
    return render_template('mydetails.html', user=current_user)


@socketio.on('message')
def message(data):
    send({'msg':data['msg'], 'username': data['username']}, room=data['room'])


@socketio.on('join')
def join(data):
    room = data['room']
    join_room(room)
    send({'msg': " joined the chat room", 'username': data['username']}, room=room)
    username = data['username']
    if username not in active_users[room]:
        active_users[room].append(username)
    users = active_users[room]
    emit('add_users', users, broadcast=True, room=room)


@socketio.on('leave')
def leave(data):
    # print(data)
    username = data['username']
    room = data['room']
    leave_room(room)
    send({'msg': " left the chat room", 'username': username}, room=room)
    active_users[room].remove(username)
    users = active_users[room]
    if len(active_users[room]) == 0:
        active_users.pop(room)
        ROOMS.remove(room)
    emit('add_users', users, broadcast=True, room=room)
    

@socketio.on('connected')
def connected(username):
    session['username'] = username


@socketio.on('disconnected')
def handle_disconnect(data):
    logout_user()
    username = data['username']
    room = data['room']
    data = {'user': username, 'msg': 'has logged out'}
    emit('system', data, broadcast=True, room=room)
    active_users[room].remove(username)
    users = active_users[room]
    if len(active_users[room]) == 0:
        active_users.pop(room)
        ROOMS.remove(room)
    emit('add_users', users, broadcast=True, room=room)