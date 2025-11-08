import datetime
import sys
import time
import os
import signal
import webbrowser
import threading
import pandas as pd

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta



# -----------------------------
# App + paths
# -----------------------------
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

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.abspath(os.path.dirname(__file__))

data_dir = os.path.join(base_dir, 'data')
os.makedirs(data_dir, exist_ok=True)

db_path = os.path.join(data_dir, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from flask_migrate import Migrate

migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

csrf = CSRFProtect(app)
app.jinja_env.globals['csrf_token'] = generate_csrf

# -----------------------------
# Models
# -----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(100), unique=True, nullable=False)
    designation = db.Column(db.String(200), nullable=False)
    serial_number = db.Column(db.String(150))
    marque = db.Column(db.String(150))
    modele = db.Column(db.String(150))
    image = db.Column(db.String(200))
    qr_code = db.Column(db.String(150))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=True)
    zone = db.relationship('Zone', backref='articles')
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=True)
    site = db.relationship('Site', backref='articles')
    local_id = db.Column(db.Integer, db.ForeignKey('locaux.id'), nullable=True)
    local = db.relationship('Locaux', backref='articles')
    famille_id = db.Column(db.Integer, db.ForeignKey('famille.id'), nullable=True)
    famille = db.relationship('Famille', backref='articles')
    sous_famille_id = db.Column(db.Integer, db.ForeignKey('sous_famille.id'), nullable=True)
    sous_famille = db.relationship('SousFamille', backref='articles')
    affecte_a = db.Column(db.String(150))
    statut = db.Column(db.String(50))  # <-- Add this
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=1))


class Famille(db.Model):
    __tablename__ = "famille"   # Explicit table name (important!)

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(80))
    type = db.Column(db.String(80))
    departement = db.Column(db.String(80))
    description = db.Column(db.String(500))

    # One-to-many relation: Famille → SousFamilles
    sous_familles = db.relationship("SousFamille", back_populates="famille", lazy=True)


class SousFamille(db.Model):
    __tablename__ = "sous_famille"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50))
    code_barres = db.Column(db.String(100))
    unite = db.Column(db.String(50))
    description = db.Column(db.Text)
    commentaire = db.Column(db.String(255))
    image = db.Column(db.String(200))

    famille_id = db.Column(db.Integer, db.ForeignKey("famille.id"), nullable=False)

    # relation back to Famille
    famille = db.relationship("Famille", back_populates="sous_familles")


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type_etablissement = db.Column(db.String(100))
    activites = db.Column(db.String(200))
    ville = db.Column(db.String(100))
    pays = db.Column(db.String(100))
    email = db.Column(db.String(120))
    telephone = db.Column(db.String(20))

    # Relation to Zone
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    zone = db.relationship('Zone', backref='sites')




class ScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code = db.Column(db.String(255), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("site.id"), nullable=True)
    famille_id = db.Column(db.Integer, db.ForeignKey("famille.id"), nullable=True)
    sous_famille_id = db.Column(db.Integer, db.ForeignKey("sous_famille.id"), nullable=True)
    designation = db.Column(db.String(255))
    serial_number = db.Column(db.String(255))
    matricule = db.Column(db.String(50))
    
    # 👇 Add this
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=1))

class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    pays = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Zone {self.nom}>"
    
class Locaux(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Relations
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    zone = db.relationship('Zone', backref='locaux')
    
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    site = db.relationship('Site', backref='locaux')
    
    batiment = db.Column(db.String(100))
    etage = db.Column(db.String(50))
    nom = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50))
    
    commentaires = db.Column(db.Text)
    dernier_inventaire = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<Locaux {self.nom}>"

class Salarie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), unique=True, nullable=False)
    nom_prenom = db.Column(db.String(100), nullable=False)
    departement = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=1))

# -----------------------------
# User loader
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



# -----------------------------
# Initialize DB
# -----------------------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('12345')
        db.session.add(admin)
        db.session.commit()


# -----------------------------
#ssss Auth routes
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('articles_list'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('articles_list'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Déconnection avec succès !", "succès")
    return redirect(url_for('login'))

# -----------------------------
# Articles Routes
# -----------------------------
@app.route('/')
@app.route('/articles')
@login_required
def articles_list():
    articles = Article.query.order_by(Article.id.desc()).all()
    return render_template('articles_list.html', articles=articles)

@app.route("/articles/add", methods=["GET", "POST"])
@app.route("/articles/edit/<int:id>", methods=["GET", "POST"])
@login_required
def article_add_edit(id=None):
    article = Article.query.get(id) if id else None

    zones = Zone.query.order_by(Zone.nom).all()
    sites = Site.query.order_by(Site.nom).all()
    locaux = Locaux.query.order_by(Locaux.nom).all()
    familles = Famille.query.order_by(Famille.nom).all()
    sous_familles = SousFamille.query.order_by(SousFamille.nom).all()
    salaries = Salarie.query.order_by(Salarie.nom_prenom).all()

    # Convert sous_familles to dicts so JS can read them
    sous_familles_data = [
        {
            "id": sf.id,
            "nom": sf.nom,
            "famille_id": sf.famille_id
        }
        for sf in sous_familles
    ]

    if request.method == "POST":
        if not article:
            article = Article()
            db.session.add(article)

        article.matricule = request.form.get('matricule')
        article.zone_id = request.form.get('zone') 
        article.site_id = request.form.get('site') 
        article.local_id = request.form.get('local') 
        article.affecte_a = request.form.get('affecte_a')
        #article.zone_affectation = request.form.get('zone_affectation')
        article.qr_code = request.form.get('qr_code')
        article.famille_id = request.form.get('famille') 
        article.sous_famille_id = request.form.get('sous_famille') 
        article.designation = request.form.get('designation')
        article.serial_number = request.form.get('serial_number')
        article.marque = request.form.get('marque')
        article.modele = request.form.get('modele')
        article.statut = request.form.get('statut')

        db.session.commit()
        flash(f"Article {'updated' if id else 'added'} successfully.", "success")
        return redirect(url_for('articles_list'))

    return render_template(
        "article_form.html",
        article=article,
        zones=zones,
        sites=sites,
        locaux=locaux,
        familles=familles,
        sous_familles=sous_familles_data,
        salaries=salaries
    )
@app.route('/article/delete/<int:id>', methods=['POST'])
@login_required
def delete_article(id):
    article = Article.query.get_or_404(id)
    db.session.delete(article)
    db.session.commit()
    flash("Article deleted successfully!", "success")
    return redirect(url_for('articles_list'))


@app.route('/articles/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_articles():
    ids = request.form.getlist('article_ids')  # name="article_ids" in checkboxes
    if not ids:
        flash("No articles selected.", "warning")
        return redirect(url_for('articles_list'))

    Article.query.filter(Article.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    flash(f"{len(ids)} article(s) deleted successfully!", "success")
    return redirect(url_for('articles_list'))

@app.route('/article/view/<int:id>', methods=['GET'])
@login_required
def view_article(id):
    article = Article.query.get_or_404(id)
    return jsonify({
        "Matricule": article.matricule,
        "Designation": article.designation,
        "Marque": article.marque,
        "Modèle": article.modele,
        "Famille": article.famille.nom if article.famille else "",
        "Sous-Famille": article.sous_famille.nom if article.sous_famille else "",
        "Site": article.site.nom if article.site else "",
        "Zone": article.zone.nom if article.zone else "",
        "Local": article.local.nom if article.local else "",
        "QR/Bar": article.qr_code,
        "Serial Number": article.serial_number,
        "Affecté à": article.affecte_a,
        #"Zone d'affectation": article.zone_affectation
    })


# -----------------------------
# Famille routes
# -----------------------------
@app.route('/famille', methods=['GET', 'POST'])
@login_required
def famille_list():
    if request.method == 'POST':
        famille_id = request.form.get('famille_id')
        if famille_id:
            famille = Famille.query.get(famille_id)
            if famille:
                db.session.delete(famille)
                db.session.commit()
                flash("Famille supprimée avec succès.", "success")
            else:
                flash("Famille introuvable.", "danger")
        return redirect(url_for('famille_list'))

    familles = Famille.query.order_by(Famille.nom.asc()).all()
    return render_template('famille.html', familles=familles)


@app.route('/famille/add', methods=['GET', 'POST'])
@login_required
def famille_add():
    if request.method == 'POST':
        famille = Famille(
            nom=request.form.get('nom'),
            code=request.form.get('code'),
            type=request.form.get('type'),
            departement=request.form.get('departement'),
            description=request.form.get('description')
        )
        db.session.add(famille)
        db.session.commit()
        flash('Famille added successfully!', 'success')
        return redirect(url_for('famille_list'))
    return render_template('famille_form.html', famille=None)

@app.route('/famille/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def famille_edit(id):
    famille = Famille.query.get_or_404(id)

    if request.method == 'POST':
        famille.nom = request.form.get('nom')
        famille.code = request.form.get('code')
        famille.type = request.form.get('type')
        famille.departement = request.form.get('departement')
        famille.description = request.form.get('description')

        db.session.commit()
        flash('Famille updated successfully!', 'success')
        return redirect(url_for('famille_list'))

    return render_template('famille_form.html', famille=famille)


@app.route('/familles/bulk-delete', methods=['POST'])
@login_required
def famille_bulk_delete():
    ids = request.form.getlist('famille_ids')  # name="famille_ids" in checkboxes
    if not ids:
        flash("No familles selected.", "warning")
        return redirect(url_for('famille_list'))

    Famille.query.filter(Famille.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    flash(f"{len(ids)} famille(s) deleted successfully!", "success")
    return redirect(url_for('famille_list'))

@app.route('/famille/delete/<int:id>', methods=['POST'])
@login_required
def famille_delete(id):
    famille = Famille.query.get_or_404(id)
    db.session.delete(famille)
    db.session.commit()
    flash('Famille deleted successfully!', 'success')
    return redirect(url_for('famille_list'))

@app.route('/famille/search')
@login_required
def famille_search():
    query = request.args.get('q', '')
    familles = Famille.query.filter(Famille.nom.ilike(f"%{query}%")).all()
    results = [{"id": f.id, "nom": f.nom} for f in familles]
    return jsonify(results)

@app.route('/famille/view/<int:id>', methods=['GET'])
@login_required
def view_famille(id):
    famille = Famille.query.get_or_404(id)
    return jsonify({
        "Nom": famille.nom,
        "Description": famille.description if hasattr(famille, 'description') else ''
    })





# -----------------------------
# Sous-Famille routes
# -----------------------------
@app.route('/sous-famille', methods=['GET', 'POST'])
@login_required
def sous_famille_list():
    if request.method == 'POST':
        sous_famille_id = request.form.get('sous_famille_id')
        if sous_famille_id:
            sous_famille = SousFamille.query.get(sous_famille_id)
            if sous_famille:
                db.session.delete(sous_famille)
                db.session.commit()
                flash("Sous-famille supprimée avec succès.", "success")
            else:
                flash("Sous-famille introuvable.", "danger")
        return redirect(url_for('sous_famille_list'))

    sous_familles = SousFamille.query.order_by(SousFamille.nom.asc()).all()
    return render_template('sous_famille.html', sous_familles=sous_familles)


@app.route('/sous-famille/add', methods=['GET', 'POST'])
@login_required
def sous_famille_add():
    if request.method == 'POST':
        sf = SousFamille(
            famille_id=request.form.get('famille_id'),  # get the selected Famille ID
            nom=request.form.get('nom'),
            code=request.form.get('code'),
            code_barres=request.form.get('code_barres'),
            unite=request.form.get('unite'),
            description=request.form.get('description'),
            commentaire=request.form.get('commentaire'),
            image=request.form.get('image')
        )
        db.session.add(sf)
        db.session.commit()
        flash('Sous-Famille added successfully!', 'success')
        return redirect(url_for('sous_famille_list'))

    # Get all familles for the dropdown
    familles = Famille.query.order_by(Famille.nom.asc()).all()
    return render_template('sous_famille_form.html', sous_famille=None, familles=familles)

@app.route('/sous-famille/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def sous_famille_edit(id):
    sous_famille = SousFamille.query.get_or_404(id)
    familles = Famille.query.order_by(Famille.nom.asc()).all()  # add this
    if request.method == 'POST':
        sous_famille.famille_id = request.form['famille_id']  # also update famille_id
        sous_famille.nom = request.form['nom']
        sous_famille.code = request.form.get('code')
        sous_famille.code_barres = request.form.get('code_barres')
        sous_famille.unite = request.form.get('unite')
        sous_famille.description = request.form.get('description')
        sous_famille.commentaire = request.form.get('commentaire')
        sous_famille.image = request.form.get('image')
        db.session.commit()
        flash('Sous-famille mise à jour avec succès', 'success')
        return redirect(url_for('sous_famille_list'))

    return render_template('sous_famille_form.html', sous_famille=sous_famille, familles=familles)

@app.route('/sous-famille/delete/<int:id>', methods=['POST'])
@login_required
def sous_famille_delete(id):
    sf = SousFamille.query.get_or_404(id)
    db.session.delete(sf)
    db.session.commit()
    flash("Sous-famille deleted successfully!", "success")
    return redirect(url_for('sous_famille_list'))




@app.route('/sous-familles/bulk-delete', methods=['POST'])
@login_required
def sous_famille_bulk_delete():
    ids = request.form.getlist('sous_famille_ids')  # name="sous_famille_ids"
    if not ids:
        flash("No sous-familles selected.", "warning")
        return redirect(url_for('sous_famille_list'))

    SousFamille.query.filter(SousFamille.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    flash(f"{len(ids)} sous-famille(s) deleted successfully!", "success")
    return redirect(url_for('sous_famille_list'))


import random
import string

@app.route('/scanner', methods=['GET', 'POST'])
@login_required
def scanner_page():
    barcode = request.args.get('barcode')
    article = None
    if barcode:
        article = Article.query.filter_by(qr_code=barcode).first()

    if request.method == 'POST':
        barcode = request.form.get('barcode')
        famille_id = request.form.get('famille')
        famille = Famille.query.get(famille_id) if famille_id else None

        if not barcode:
            flash("Barcode is required!", "danger")
            return redirect(url_for('scanner_page'))

        # Check if article exists
        article = Article.query.filter_by(qr_code=barcode).first()
        if not article:
            # Generate matricule: use famille code if available + random digits
            code_part = famille.code.upper() if famille and famille.code else ''.join(random.choices(string.ascii_uppercase, k=2))
            random_part = ''.join(random.choices(string.digits, k=8))
            matricule = f"{code_part}{random_part}"
            article = Article(qr_code=barcode, matricule=matricule)
            db.session.add(article)

        # Update article fields from form
        article.zone_id = request.form.get('zone') or None
        article.site_id = request.form.get('site') or None
        article.local_id = request.form.get('local') or None
        article.affecte_a = request.form.get('affecte_a')
        article.famille_id = famille_id or None
        article.sous_famille_id = request.form.get('sous_famille') or None
        article.designation = request.form.get('designation')
        article.serial_number = request.form.get('serial_number')
        article.marque = request.form.get('marque')
        article.modele = request.form.get('modele')
        article.statut = request.form.get('statut')

        db.session.commit()
        flash("Article saved successfully!", "success")
        return redirect(url_for('scanner_page', barcode=barcode))  # Keep barcode to pre-fill

    # Load dropdowns and history
    familles = [{"id": f.id, "nom": f.nom, "code": f.code} for f in Famille.query.order_by(Famille.nom).all()]
    sous_familles = [{"id": sf.id, "nom": sf.nom, "famille_id": sf.famille_id} for sf in SousFamille.query.order_by(SousFamille.nom).all()]
    sites = [{"id": s.id, "nom": s.nom} for s in Site.query.order_by(Site.nom).all()]
    zones = Zone.query.order_by(Zone.nom).all()
    locaux = Locaux.query.order_by(Locaux.nom).all()
    history = Article.query.order_by(Article.id.desc()).limit(10).all()
    salaries = Salarie.query.order_by(Salarie.nom_prenom).all()

    return render_template(
        'scanner.html',
        familles=familles,
        sous_familles=sous_familles,
        sites=sites,
        zones=zones,
        locaux=locaux,
        articles=history,
        article=article,
        salaries=salaries
    )
# -----------------------------
# API: Get Article by Barcode
# -----------------------------
@app.route('/article/get/<string:barcode>', methods=['GET'])
def get_article_by_barcode(barcode):
    article = Article.query.filter_by(qr_code=barcode).first()
    if not article:
        return jsonify({"message": "Article not found"}), 404

    return jsonify({
        "id": article.id,
        "matricule": article.matricule,
        "zone_id": article.zone_id,
        "site_id": article.site_id,
        "local_id": article.local_id,
        "affecte_a": article.affecte_a if article.affecte_a else "",
        "famille_id": article.famille_id,
        "sous_famille_id": article.sous_famille_id,
        "designation": article.designation,
        "serial_number": article.serial_number,
        "marque": article.marque,
        "modele": article.modele,
        "statut": article.statut
    }), 200
# -----------------------------
# Localisation Routes
# -----------------------------

# ---- LIST ZONES ----
@app.route("/zones", methods=['GET', 'POST'])
@login_required
def zones_list():
    if request.method == 'POST':
        zone_id = request.form.get('zone_id')
        if zone_id:
            zone = Zone.query.get(zone_id)
            if zone:
                db.session.delete(zone)
                db.session.commit()
                flash("Zone supprimée avec succès.", "success")
            else:
                flash("Zone introuvable.", "danger")
        return redirect(url_for('zones_list'))

    zones = Zone.query.order_by(Zone.nom.asc()).all()
    return render_template("zones.html", zones=zones)

# ---- ADD ZONE ----
@app.route("/zones/add", methods=["GET", "POST"])
def zone_add():
    if request.method == "POST":
        nom = request.form.get("nom")
        pays = request.form.get("pays")

        if not nom or not pays:
            flash("Both name and country are required!", "danger")
            return redirect(url_for("zone_add"))

        new_zone = Zone(nom=nom, pays=pays)
        db.session.add(new_zone)
        db.session.commit()
        flash("Zone added successfully!", "success")
        return redirect(url_for("zones_list"))

    return render_template("zone_form.html", zone=None)


# ---- EDIT ZONE ----
@app.route("/zones/edit/<int:id>", methods=["GET", "POST"])
def zone_edit(id):
    zone = Zone.query.get_or_404(id)

    if request.method == "POST":
        zone.nom = request.form.get("nom")
        zone.pays = request.form.get("pays")

        db.session.commit()
        flash("Zone modifiée avec succés!", "success")
        return redirect(url_for("zones_list"))

    return render_template("zone_form.html", zone=zone)


# ---- DELETE ZONE ----
@app.route("/zones/delete/<int:id>", methods=["POST"])
def delete_zone(id):
    zone = Zone.query.get_or_404(id)
    db.session.delete(zone)
    db.session.commit()
    flash("Zone deleted successfully!", "success")
    return redirect(url_for("zones_list"))


# ---- BULK DELETE ----
@app.route('/zones/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_zones():
    ids = request.form.getlist('zone_ids')  # name="zone_ids"
    if not ids:
        flash("No zones selected.", "warning")
        return redirect(url_for('zones_list'))

    Zone.query.filter(Zone.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    flash(f"{len(ids)} zone(s) deleted successfully!", "success")
    return redirect(url_for('zones_list'))

# ----------------------------- Sites Routes -----------------------------
@app.route('/sites', methods=['GET', 'POST'])
@login_required
def sites():
    

    # Handle bulk delete
    if request.method == 'POST' and 'site_ids' in request.form:
        ids = request.form.getlist('site_ids')
        Site.query.filter(Site.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f"{len(ids)} site(s) deleted successfully!", "success")
        return redirect(url_for('sites'))

    sites = Site.query.all()
    zones = Zone.query.all()
    return render_template('sites.html', sites=sites, zones=zones)


@app.route('/site_add', methods=['GET', 'POST'])
@login_required
def site_add():
    

    zones = Zone.query.all()
    site_id = request.args.get('id')
    site = Site.query.get(site_id) if site_id else None

    if request.method == 'POST':
        nom = request.form['nom']
        type_etablissement = request.form['type_etablissement']
        activites = request.form['activites']
        ville = request.form['ville']
        pays = request.form['pays']
        email = request.form['email']
        telephone = request.form['telephone']
        zone_id = request.form['zone_id']

        if site:
            # Edit existing
            site.nom = nom
            site.type_etablissement = type_etablissement
            site.activites = activites
            site.ville = ville
            site.pays = pays
            site.email = email
            site.telephone = telephone
            site.zone_id = zone_id
            flash("Site updated successfully!", "success")
        else:
            # Add new
            new_site = Site(
                nom=nom,
                type_etablissement=type_etablissement,
                activites=activites,
                ville=ville,
                pays=pays,
                email=email,
                telephone=telephone,
                zone_id=zone_id
            )
            db.session.add(new_site)
            flash("Site added successfully!", "success")
        db.session.commit()
        return redirect(url_for('sites'))

    return render_template('site_add.html', zones=zones, site=site)


@app.route('/site_delete/<int:id>', methods=['POST'])
@login_required
def site_delete(id):
    site = Site.query.get_or_404(id)
    db.session.delete(site)
    db.session.commit()
    flash("Site deleted successfully!", "success")
    return redirect(url_for('sites'))

# ----------------------------- Locaux Routes -----------------------------
@app.route('/locaux', methods=['GET', 'POST'])
@login_required
def locaux():
    

    # Bulk delete
    if request.method == 'POST' and 'locaux_ids' in request.form:
        ids = request.form.getlist('locaux_ids')
        Locaux.query.filter(Locaux.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f"{len(ids)} locaux deleted successfully!", "success")
        return redirect(url_for('locaux'))

    locaux_list = Locaux.query.all()
    zones = Zone.query.all()
    sites = Site.query.all()
    return render_template('locaux.html', locaux_list=locaux_list, zones=zones, sites=sites)


@app.route('/locaux_add', methods=['GET', 'POST'])
@login_required
def locaux_add():
    

    zones = Zone.query.all()
    sites = Site.query.all()
    locaux_id = request.args.get('id')
    locaux_item = Locaux.query.get(locaux_id) if locaux_id else None

    if request.method == 'POST':
        zone_id = request.form['zone_id']
        site_id = request.form['site_id']
        batiment = request.form['batiment']
        etage = request.form['etage']
        nom = request.form.get('nom')
        code = request.form['code']
        
        commentaires = request.form['commentaires']

        if locaux_item:
            # Edit
            locaux_item.zone_id = zone_id
            locaux_item.site_id = site_id
            locaux_item.batiment = batiment
            locaux_item.etage = etage
            locaux_item.nom = nom
            locaux_item.code = code
            
            locaux_item.commentaires = commentaires
            flash("Locaux updated successfully!", "success")
        else:
            # Add new
            new_locaux = Locaux(
                zone_id=zone_id,
                site_id=site_id,
                batiment=batiment,
                etage=etage,
                nom=nom,
                code=code,
                commentaires=commentaires
            )
            db.session.add(new_locaux)
            flash("Locaux added successfully!", "success")

        db.session.commit()
        return redirect(url_for('locaux'))

    return render_template('locaux_add.html', zones=zones, sites=sites, locaux=locaux_item)


@app.route('/locaux_delete/<int:id>', methods=['POST'])
@login_required
def locaux_delete(id):
    locaux_item = Locaux.query.get_or_404(id)
    db.session.delete(locaux_item)
    db.session.commit()
    flash("Locaux deleted successfully!", "success")
    return redirect(url_for('locaux'))

@app.route('/locaux/delete', methods=['POST'])
def locaux_bulk_delete():
    ids = request.form.getlist('locaux_ids')  # checkbox values
    for id in ids:
        l = Locaux.query.get(id)
        if l:
            db.session.delete(l)
    db.session.commit()
    flash(f"{len(ids)} locaux deleted.", "success")
    return redirect(url_for('locaux'))

@app.route('/salaries')
@login_required
def liste_salaries():
    # Replace with your actual model for employees
    salaries = Salarie.query.order_by(Salarie.nom_prenom).all()
    return render_template('salaries_list.html', salaries=salaries)

@app.route('/salarie', methods=['GET', 'POST'])
@app.route('/salarie/<int:id>', methods=['GET', 'POST'])
@login_required
def salarie_add_edit(id=None):
    """
    Add a new salarie if id is None, else edit existing salarie
    """
    salarie = None
    if id:
        salarie = Salarie.query.get_or_404(id)

    if request.method == 'POST':
        matricule = request.form.get('matricule').strip()
        nom_prenom = request.form.get('nom_prenom').strip()
        departement = request.form.get('departement').strip()

        # Validate
        if not matricule or not nom_prenom or not departement:
            flash("All fields are required!", "danger")
            return redirect(request.url)

        if salarie:  # Edit
            salarie.matricule = matricule
            salarie.nom_prenom = nom_prenom
            salarie.departement = departement
            flash("Salarie updated successfully!", "success")
        else:  # Add
            # Check duplicate matricule
            if Salarie.query.filter_by(matricule=matricule).first():
                flash("Matricule already exists!", "danger")
                return redirect(request.url)

            salarie = Salarie(matricule=matricule, nom_prenom=nom_prenom, departement=departement)
            db.session.add(salarie)
            flash("Salarie added successfully!", "success")

        db.session.commit()
        return redirect(url_for('liste_salaries'))

    return render_template('salarie_add_edit.html', salarie=salarie)

@app.route('/salaries/bulk_delete', methods=['POST'])
@login_required
def bulk_delete_salaries():
    salarie_ids = request.form.getlist('salarie_ids')
    if not salarie_ids:
        flash("No salaries selected!", "warning")
        return redirect(url_for('liste_salaries'))

    # Delete selected salaries
    try:
        Salarie.query.filter(Salarie.id.in_(salarie_ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f"{len(salarie_ids)} salaries deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting salaries: {str(e)}", "danger")

    return redirect(url_for('liste_salaries'))

from flask import request, jsonify
import pandas as pd
from datetime import datetime

@app.route('/import_salaries', methods=['POST'])
def import_salaries():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        df = pd.read_excel(file)

        for _, row in df.iterrows():
            # Convert to string safely
            matricule = str(row.get("Matricule", "")).strip() if pd.notna(row.get("Matricule")) else ""
            nom_prenom = str(row.get("Nom et Prénom", "")).strip() if pd.notna(row.get("Nom et Prénom")) else ""
            departement = str(row.get("Département", "")).strip() if pd.notna(row.get("Département")) else ""

            if not matricule:
                # Skip rows with empty matricule
                continue

            # Check if salarie already exists
            existing = Salarie.query.filter_by(matricule=matricule).first()
            if existing:
                existing.nom_prenom = nom_prenom
                existing.departement = departement
            else:
                new_salarie = Salarie(
                    matricule=matricule,
                    nom_prenom=nom_prenom,
                    departement=departement,
                    created_at=datetime.utcnow() + timedelta(hours=1)
                )
                db.session.add(new_salarie)

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
# -----------------------------
# Helpers
# -----------------------------
#def shutdown_server():
#    os.kill(os.getpid(), signal.SIGTERM)


def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000")






if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    app.run(host='0.0.0.0', port=5000)
