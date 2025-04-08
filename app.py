from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, IntegerField, FloatField, TextAreaField, SubmitField
from wtforms.validators import InputRequired, NumberRange
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import io
import csv
import os
from fleet_routes import fleet_bp


app = Flask(__name__)
app.secret_key = 'your_secret_key'
csrf = CSRFProtect(app)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.register_blueprint(fleet_bp)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, name, role):
        self.id = id
        self.name = name
        self.role = role

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['name'], user['role'])
    return None

@app.context_processor
def inject_user():
    return dict(user=current_user)

from datetime import datetime

@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}
 
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

class LoginForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Register')

class MaterialForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    quantity = IntegerField('Quantity', validators=[InputRequired(), NumberRange(min=0)])
    unit = StringField('Unit', validators=[InputRequired()])
    unit_price = FloatField('Unit Price', validators=[InputRequired(), NumberRange(min=0)])
    supplier = StringField('Supplier', validators=[InputRequired()])
    material_type = StringField('Material Type', validators=[InputRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Add Material')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        password = generate_password_hash(form.password.data.strip())
        role = 'crew_member'
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, password, role) VALUES (?, ?, ?)', (name, password, role))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
            return redirect(url_for('register'))
        finally:
            conn.close()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        password = form.password.data.strip()
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE name = ?', (name,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['name'], user['role'])
            login_user(user_obj)
            return redirect(url_for('materials'))
        flash("Invalid credentials.", "error")
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/materials')
@login_required
def materials():
    conn = get_db_connection()
    materials = conn.execute('SELECT * FROM materials').fetchall()
    conn.close()
    return render_template('materials.html', materials=materials)

@app.route('/add_material', methods=['GET', 'POST'])
@login_required
def add_material():
    form = MaterialForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO materials (name, quantity, unit, unit_price, supplier, material_type, description, user_id) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (form.name.data, form.quantity.data, form.unit.data, form.unit_price.data, 
             form.supplier.data, form.material_type.data, form.description.data, current_user.id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('materials'))
    return render_template('add_material.html', form=form)

@app.route('/export_csv')
@login_required
def export_csv():
    conn = get_db_connection()
    materials = conn.execute('SELECT * FROM materials').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Quantity', 'Unit', 'Unit Price', 'Supplier', 'Type', 'Description'])

    for m in materials:
        writer.writerow([
            m['name'], m['quantity'], m['unit'], m['unit_price'],
            m['supplier'], m['material_type'], m['description']
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='materials.csv'
    )

@app.route('/edit_material/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_material(id):
    conn = get_db_connection()
    material = conn.execute('SELECT * FROM materials WHERE id = ?', (id,)).fetchone()

    if not material:
        flash("Material not found.", "danger")
        return redirect(url_for('materials'))

    form = MaterialForm(data=material)

    if form.validate_on_submit():
        conn.execute('''
            UPDATE materials
            SET name = ?, quantity = ?, unit = ?, unit_price = ?, supplier = ?, material_type = ?, description = ?
            WHERE id = ?
        ''', (
            form.name.data, form.quantity.data, form.unit.data, form.unit_price.data,
            form.supplier.data, form.material_type.data, form.description.data, id
        ))
        conn.commit()
        conn.close()
        flash("Material updated successfully!", "success")
        return redirect(url_for('materials'))

    conn.close()
    return render_template('add_material.html', form=form, edit=True)

@app.route('/delete_material/<int:id>', methods=['POST'])
@login_required
def delete_material(id):
    if current_user.role != 'admin':
        flash("You are not authorized to delete materials.", "danger")
        return redirect(url_for('materials'))

    conn = get_db_connection()
    conn.execute('DELETE FROM materials WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Material deleted.", "info")
    return redirect(url_for('materials'))

@app.route('/update_quantity/<int:id>', methods=['GET', 'POST'])
@login_required
def update_quantity(id):
    if current_user.role not in ['crew_member', 'crew_leader', 'admin']:
        flash("You are not authorized to update quantity.", "danger")
        return redirect(url_for('materials'))

    conn = get_db_connection()
    material = conn.execute('SELECT * FROM materials WHERE id = ?', (id,)).fetchone()

    if not material:
        conn.close()
        flash("Material not found.", "danger")
        return redirect(url_for('materials'))

    class QuantityForm(FlaskForm):
        quantity = IntegerField('Quantity', validators=[InputRequired(), NumberRange(min=0)])
        submit = SubmitField('Update')

    form = QuantityForm(quantity=material['quantity'])

    if form.validate_on_submit():
        new_quantity = form.quantity.data
        conn.execute('UPDATE materials SET quantity = ? WHERE id = ?', (new_quantity, id))
        conn.commit()
        conn.close()
        flash("Quantity updated.", "success")
        return redirect(url_for('materials'))

    conn.close()
    return render_template('update_quantity.html', form=form, material=material)

if __name__ == '__main__':
    app.run(debug=True)
