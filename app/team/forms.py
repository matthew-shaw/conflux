from flask_wtf import FlaskForm
from govuk_frontend_wtf.wtforms_widgets import (
    GovCheckboxInput,
    GovRadioInput,
    GovSubmitInput,
    GovTextInput,
)
from wtforms.fields import BooleanField, RadioField, StringField, SubmitField
from wtforms.validators import InputRequired, ValidationError

from app.models import Team


class TeamForm(FlaskForm):
    name = StringField(
        "Name",
        filters=[lambda x: x.strip() if x else x],
        widget=GovTextInput(),
        validators=[InputRequired(message="Enter a name")],
    )
    submit: SubmitField = SubmitField("Save", widget=GovSubmitInput())

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team

    def validate_name(self, field):
        existing_team = Team.query.filter_by(name=field.data).first()

        if existing_team and (self.team is None or existing_team.id != self.team.id):
            raise ValidationError("A team with this name already exists.")


class TeamSortFilterForm(FlaskForm):
    sort = RadioField(
        "Sort by",
        widget=GovRadioInput(),
        choices=[
            ("name", "Name"),
            ("updated", "Updated"),
        ],
        default="name",
    )
    status = RadioField(
        "Status",
        widget=GovRadioInput(),
        choices=[("all", "All"), ("active", "Active"), ("archived", "Archived")],
        default="active",
    )


class ArchiveTeamForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to archive this team")],
    )
    submit: SubmitField = SubmitField("Archive", widget=GovSubmitInput())


class RestoreTeamForm(FlaskForm):
    confirm = BooleanField(
        "I'm sure",
        widget=GovCheckboxInput(),
        validators=[InputRequired(message="Select if you want to restore this team")],
    )
    submit: SubmitField = SubmitField("Restore", widget=GovSubmitInput())
