import sys
import time
import os
import signal
import webbrowser
import threading

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf


# Determine base path for templates and static folders
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

app = Flask(
    __name__,
    template_folder=os.path.join(base_path, "templates"),
    static_folder=os.path.join(base_path, "static")
)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Persistent DB path logic
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.abspath(os.path.dirname(__file__))

data_dir = os.path.join(base_dir, 'data')
os.makedirs(data_dir, exist_ok=True)

db_path = os.path.join(data_dir, 'clients.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

csrf = CSRFProtect(app)
app.jinja_env.globals['csrf_token'] = generate_csrf


# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(200))
    name = db.Column(db.String(200))
    phone = db.Column(db.String(80))
    email = db.Column(db.String(120))
    ice = db.Column(db.String(80))
    ifNumber = db.Column(db.String(80))
    rc = db.Column(db.String(80))
    tp = db.Column(db.String(80))
    cnss = db.Column(db.String(80))
    cnssLogin = db.Column(db.String(120))
    cnssPassword = db.Column(db.String(120))
    dgiLogin = db.Column(db.String(120))
    dgiPassword = db.Column(db.String(120))
    adhesionLogin = db.Column(db.String(120))
    adhesionPassword = db.Column(db.String(120))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='Amine').first():
        admin = User(username='Amine')
        admin.set_password('12345')  # default - change in production
        db.session.add(admin)
        db.session.commit()


# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('clients_list'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('clients_list'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    shutdown_server()
    return "Application closed."


@app.route('/')
@login_required
def clients_list():
    clients = Client.query.order_by(Client.company.asc()).all()
    return render_template('clients_list.html', clients=clients)


@app.route('/form', methods=['GET', 'POST'])
@login_required
def client_form():
    if request.method == 'POST':
        fields = ['company', 'name', 'phone', 'email', 'ice', 'ifNumber', 'rc', 'tp', 'cnss', 'cnssLogin', 'cnssPassword',
                  'dgiLogin', 'dgiPassword', 'adhesionLogin', 'adhesionPassword']
        data = {k: request.form.get(k) for k in fields}
        client = Client(**data)
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully!', 'success')
        return redirect(url_for('clients_list'))
    return render_template('client_form.html')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_client(id):
    client = Client.query.get_or_404(id)
    if request.method == 'POST':
        for field in ['company', 'name', 'phone', 'email', 'ice', 'ifNumber', 'rc', 'tp', 'cnss', 'cnssLogin', 'cnssPassword',
                      'dgiLogin', 'dgiPassword', 'adhesionLogin', 'adhesionPassword']:
            setattr(client, field, request.form.get(field))
        db.session.commit()
        flash('Client updated successfully!', 'success')
        return redirect(url_for('clients_list'))
    return render_template('edit_client.html', client=client)


@app.route('/view/<int:id>')
@login_required
def view_client(id):
    client = Client.query.get_or_404(id)
    return render_template('view_client.html', client=client)


@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_client(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash('Client deleted successfully!', 'success')
    return redirect(url_for('clients_list'))


def shutdown_server():
    os.kill(os.getpid(), signal.SIGTERM)


def open_browser():
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    app.run(host='0.0.0.0', port=5000)
