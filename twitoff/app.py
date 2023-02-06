"""Main APP/routing file for TwitOff."""
from os import getenv
from dotenv import load_dotenv
from flask import Flask, render_template, request
from twitoff.models import DB, User
from twitoff.predict import predict_user
from twitoff.twitter import add_or_update_user, update_all_users


"""Create and configure an instance of the Flask application."""
load_dotenv()
APP = Flask(__name__)
APP.config['SQLALCHEMY_DATABASE_URI'] = getenv('DATABASE_URL')
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB.init_app(APP)


@APP.route('/')
def root():
    return render_template('base.html', title='Home', users=User.query.all())


@APP.route('/user', methods=['POST'])
@APP.route('/user/<name>', methods=['GET'])
def user(name=None, message=''):
    name = name or request.values['user_name']
    try:
        if request.method == 'POST':
            add_or_update_user(name)
            message = "User {} successfully added!".format(name)
        tweets = User.query.filter(User.name == name).one().tweets
    except Exception as e:
        message = "Error adding {}: {}".format(name, e)
        tweets = []
    return render_template('user.html', title=name, tweets=tweets,
                           message=message)


@APP.route('/compare', methods=['POST'])
def compare():
    user1, user2 = sorted([request.values['user1'],
                           request.values['user2']])
    if user1 == user2:
        message = 'Cannot compare a user to themselves!'
    else:
        prediction = predict_user(user1, user2, request.values['tweet_text'])
        message = '"{}" is more likely to be said by {} than {}'.format(
            request.values['tweet_text'], user1 if prediction else user2,
            user2 if prediction else user1)
    return render_template('prediction.html', title='Prediction', message=message)


@APP.route('/reset')
def reset():
    DB.drop_all()
    DB.create_all()
    return render_template('base.html', title='Reset database!')


@APP.route('/update')
def update():
    update_all_users()
    return render_template('base.html', users=User.query.all(),
                           title='All Tweets updated!')
