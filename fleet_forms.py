
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, TextAreaField, FileField, SubmitField
from wtforms.validators import InputRequired, Optional

class EquipmentForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    type = StringField('Type', validators=[InputRequired()])
    make = StringField('Make', validators=[Optional()])
    model = StringField('Model', validators=[Optional()])
    year = IntegerField('Year', validators=[Optional()])
    mileage = IntegerField('Mileage', validators=[Optional()])
    oil_change_due = DateField('Oil Change Due', validators=[Optional()])
    inspection_due = DateField('Inspection Due', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    image = FileField('Upload Image')
    submit = SubmitField('Add Equipment')

class ServiceLogForm(FlaskForm):
    service_date = DateField('Service Date', validators=[InputRequired()])
    description = TextAreaField('Service Description', validators=[Optional()])
    photo = FileField('Upload Photo')
    submit = SubmitField('Add Service Log')
