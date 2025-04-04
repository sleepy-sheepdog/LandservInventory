from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, IntegerField, FloatField, TextAreaField, SubmitField
from wtforms.validators import InputRequired, NumberRange
from flask import send_file
import io
import csv


app = Flask(__name__)
app.secret_key = 'your_secret_key'
csrf = CSRFProtect(app)
@app.context_processor
def inject_user():
    return dict(user=g.user)


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    if user_id:
        conn = get_db_connection()
        g.user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
       


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
            session['user_id'] = user['id']
            return redirect(url_for('materials'))
        flash("Invalid credentials.", "error")
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/materials')
def materials():
    conn = get_db_connection()
    materials = conn.execute('SELECT * FROM materials').fetchall()
    conn.close()
    return render_template('materials.html', materials=materials)

@app.route('/add_material', methods=['GET', 'POST'])
def add_material():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    form = MaterialForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO materials (name, quantity, unit, unit_price, supplier, material_type, description, user_id) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (form.name.data, form.quantity.data, form.unit.data, form.unit_price.data, 
             form.supplier.data, form.material_type.data, form.description.data, session['user_id'])
        )
        conn.commit()
        conn.close()
        return redirect(url_for('materials'))
    return render_template('add_material.html', form=form)
@app.route('/export_csv')
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
def edit_material(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
def delete_material(id):
    if not g.user or g.user['role'] != 'admin':
        flash("You are not authorized to delete materials.", "danger")
        return redirect(url_for('materials'))

    conn = get_db_connection()
    conn.execute('DELETE FROM materials WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Material deleted.", "info")
    return redirect(url_for('materials'))
@app.route('/update_quantity/<int:id>', methods=['GET', 'POST'])
def update_quantity(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if g.user['role'] not in ['crew_member', 'crew_leader']:
        flash("Only crew members or leaders can update quantity.", "danger")
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

    