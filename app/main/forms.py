from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User

class SearchForm(FlaskForm):
    search = StringField('书名、作者、ISBN', validators=[Required()], render_kw={"placeholder": "书名、作者、ISBN"})
    submit = SubmitField('搜索')

class ApplyForm(FlaskForm):
    submit = SubmitField('确认')


class NameForm(FlaskForm):
    name = StringField('请输入你的用户名', validators=[Required()])
    submit = SubmitField('提交')


class EditProfileForm(FlaskForm):
    name = StringField('真实姓名', validators=[Length(0, 64)])
    location = StringField('所在学校', validators=[Length(0, 64)])
    about_me = TextAreaField('个人简介')
    submit = SubmitField('提交')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    username = StringField('用户名', validators=[
        Required(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                          'Usernames must have only letters, '
                                          'numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('用户等级', coerce=int)
    name = StringField('真实姓名', validators=[Length(0, 64)])
    location = StringField('所在学校', validators=[Length(0, 64)])
    about_me = TextAreaField('个人简介')
    submit = SubmitField('提交')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class PostForm(FlaskForm):
    body = PageDownField("What's on your mind?", validators=[Required()])
    submit = SubmitField('Submit')


class CommentForm(FlaskForm):
    body = StringField('Enter your comment', validators=[Required()])
    submit = SubmitField('Submit')
