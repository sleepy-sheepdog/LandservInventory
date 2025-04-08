
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3

from fleet_forms import EquipmentForm, ServiceLogForm

fleet_bp = Blueprint('fleet', __name__)
UPLOAD_FOLDER = 'static/uploads'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@fleet_bp.route('/equipment')
@login_required
def equipment():
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment').fetchall()
    conn.close()
    return render_template('equipment.html', equipment=equipment)

@fleet_bp.route('/equipment/add', methods=['GET', 'POST'])
@login_required
def add_equipment():
    form = EquipmentForm()
    if form.validate_on_submit():
        image_path = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(UPLOAD_FOLDER, filename))
            image_path = filename

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO equipment 
            (name, type, make, model, year, mileage, oil_change_due, inspection_due, notes, image_path, added_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            form.name.data, form.type.data, form.make.data, form.model.data, form.year.data,
            form.mileage.data, form.oil_change_due.data, form.inspection_due.data,
            form.notes.data, image_path, current_user.id
        ))
        conn.commit()
        conn.close()
        flash('Equipment added successfully!', 'success')
        return redirect(url_for('fleet.equipment'))

    return render_template('add_equipment.html', form=form)

@fleet_bp.route('/equipment/<int:id>')
@login_required
def view_equipment(id):
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment WHERE id = ?', (id,)).fetchone()
    service_logs = conn.execute('SELECT * FROM service_logs WHERE equipment_id = ? ORDER BY service_date DESC', (id,)).fetchall()
    conn.close()

    if not equipment:
        flash('Equipment not found.', 'danger')
        return redirect(url_for('fleet.equipment'))

    return render_template('equipment_detail.html', equipment=equipment, service_logs=service_logs)

@fleet_bp.route('/equipment/<int:id>/add_service', methods=['GET', 'POST'])
@login_required
def add_service_log(id):
    form = ServiceLogForm()
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment WHERE id = ?', (id,)).fetchone()

    if not equipment:
        flash('Equipment not found.', 'danger')
        return redirect(url_for('fleet.equipment'))

    if form.validate_on_submit():
        photo_path = None
        if form.photo.data:
            filename = secure_filename(form.photo.data.filename)
            form.photo.data.save(os.path.join(UPLOAD_FOLDER, filename))
            photo_path = filename

        conn.execute('''
            INSERT INTO service_logs (equipment_id, service_date, description, photo_path, added_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            id, form.service_date.data, form.description.data, photo_path, current_user.id
        ))
        conn.commit()
        conn.close()
        flash('Service log added!', 'success')
        return redirect(url_for('fleet.view_equipment', id=id))

    conn.close()
    return render_template('add_service_log.html', form=form, equipment=equipment)
