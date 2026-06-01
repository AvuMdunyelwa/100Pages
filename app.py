import os
from flask import *
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from psutil import users
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date
from help import login_required
from api import search_for_song


# Configure CS50 Library to use SQLite database
print("DATABASE_URL:", os.environ.get("DATABASE_URL"))
db = SQL(os.environ.get("DATABASE_URL"))

#creating a news_letter table in the db
db.execute('CREATE TABLE IF NOT EXISTS newsletter ( id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, email TEXT NOT NULL UNIQUE, FOREIGN KEY (user_id) REFERENCES users(id))')

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route('/')
def landing_page():
    message = request.args.get('message')
    # popular songs based on average rating
    popular_songs = db.execute('SELECT cover_img_url, AVG(rating) AS average_rating FROM reviews WHERE reviews.created_at >= date("now", "-30 days") GROUP BY track_id ORDER BY AVG(rating) DESC LIMIT 5')
    # popular reviews based on likes
    reviews = db.execute('SELECT reviews.id AS review_id, reviews.song_title, reviews.artist, reviews.review_content, reviews.rating, reviews.cover_img_url, users.username, COUNT(likes.review_id) AS total_likes FROM reviews JOIN users ON users.id = reviews.user_id LEFT JOIN likes ON reviews.id = likes.review_id GROUP BY reviews.id ORDER BY total_likes DESC LIMIT 10')

    if session.get('user_id'):
        user_id = session['user_id']
        username = db.execute('SELECT username FROM users WHERE id=?', user_id)

        for review in reviews:
            existing_likes = db.execute('SELECT * FROM likes WHERE user_id=? AND review_id=?', session["user_id"], review["review_id"])
            if existing_likes:
                review["liked"] = True
            else:
                review["liked"] = False

        return render_template('homeFeed.html', username=username[0]['username'], reviews=reviews, popular_songs=popular_songs, message=message)

    return render_template('index.html', reviews=reviews, popular_songs=popular_songs)


@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route('/login', methods=['POST', 'GET'])
def login():
    """ Log user in """
    # get message
    message = request.args.get('message') 
    # forget user id
    session.clear()

    if request.method == 'POST':
        # get user login details
        username = request.form.get('username')
        password = request.form.get('password')

        # ensure username and password was submitted
        if not username:
            error = 'Enter valid username'
            return render_template("login.html", message=error)
        elif not password:
            error = 'Enter valid password'
            return render_template("login.html", message=error)

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", username
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["password_hash"], password
        ):
            error = 'invalid username and/or password'
            return render_template("login.html", message=error)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect(url_for("landing_page"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    error = None
    if request.method == 'POST':

        # check if password and username are valid
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')
        email = request.form.get('email')
        username = request.form.get('username')

        if not username:
            error = 'invalid username'
            return render_template("register.html", message=error)

        if not email:
            error = 'invalid email'
            return render_template("register.html", message=error)

        if not password or password != confirmation:
            error = 'invalid password do not match'
            return render_template("register.html", message=error)
        try:
            db.execute('INSERT INTO users (username, email, password_hash) VALUES(?,?,?)',
                       username, email, generate_password_hash(password))
            return redirect('/login')
        except ValueError:
            error = 'Username already exists'
            return render_template("register.html", message=error)

    else:
        return render_template('register.html')

@app.route("/song", methods=["POST"])
def find_track():
    """ get search results """

    song = request.form.get("song")
    artist = request.form.get("artist")

    if not song:
        error = "Please enter a song title"
        return render_template("music.html", message=error)

    songs = search_for_song(song,artist)

    if not songs:
        error = f"no results found for: {song}"
        return render_template("music.html", message=error)
    try:
        # display song details
        return render_template("music.html", songs=songs, input=song)
    except ValueError:
        # no song found
        error = f"no results found for: {song}"
        return render_template("music.html", message=error)


@app.route("/review", methods=["POST"])
@login_required
def store_review():
    """ store the review data to the database """

    user_id = session["user_id"]
    track_id = request.form.get("id")
    track_title = request.form.get("title")
    track_artist = request.form.get("artist")
    track_img = request.form.get("img")
    review = request.form.get("review")
    rating = request.form.get("rating")


    if not rating or int(rating) < 1 or int(rating) > 5:
        error = 'Please provide a valid rating (1-5)'
        return render_template("music.html", message=error)

    if not track_id or not track_title or not track_artist or not track_img:
        error = 'Invalid track information. Please try again.'
        return render_template("music.html", message=error)

    if not review:
        error = 'Please provide a review.'
        return render_template("music.html", message=error)

    db.execute('INSERT INTO reviews (user_id, track_id, song_title, artist, cover_img_url, review_content, rating) VALUES(?,?,?,?,?,?,?)',
               user_id, track_id, track_title, track_artist, track_img, review, rating)

    return redirect('/account')


@app.route("/account", methods=["GET"])
@login_required
def profile():
    """ show the user's profile page with their reviews """

    user_id = session["user_id"]
    username = db.execute('SELECT username FROM users WHERE id=?', user_id)
    reviews = db.execute('SELECT reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist, COUNT(likes.id) AS total_likes FROM reviews LEFT JOIN likes ON likes.review_id = reviews.id WHERE reviews.user_id = ? GROUP BY reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist', user_id)
    return render_template("profile.html", username=username[0]['username'], reviews=reviews)

@app.route("/reviews", methods=["GET"])
def reviews():
    """ show all reviews """

    # popular songs based on average rating
    popular_songs = db.execute('SELECT cover_img_url, AVG(rating) AS average_rating FROM reviews GROUP BY track_id ORDER BY AVG(rating) DESC LIMIT 5')

    # popular reviews based on likes
    reviews = db.execute('SELECT reviews.id AS review_id, reviews.song_title, reviews.artist, reviews.review_content, reviews.rating, reviews.cover_img_url, users.username, COUNT(likes.review_id) AS total_likes FROM reviews JOIN users ON users.id = reviews.user_id LEFT JOIN likes ON reviews.id = likes.review_id GROUP BY reviews.id ORDER BY created_at DESC LIMIT 10')
    for review in reviews:
        existing_likes = db.execute('SELECT * FROM likes WHERE user_id=? AND review_id=?', session["user_id"], review["review_id"])
        if existing_likes:
            review["liked"] = True
        else:
            review["liked"] = False

    # top reviewers
    top_reviewers = db.execute('SELECT username, COUNT(reviews.id) AS review_count FROM users JOIN reviews ON reviews.user_id = users.id GROUP BY users.id ORDER BY COUNT(reviews.id) DESC LIMIT 5')

    return render_template("reviews.html", reviews=reviews, popular_songs=popular_songs, top_reviewers=top_reviewers)


@app.route("/likes", methods=["POST"])
@login_required
def like_review():
    """ allow users to like a review """

    review_id = int(request.form.get("review_id"))
    user_id = session["user_id"]

    if not review_id:
        return redirect("/reviews")

    # check if the user has already liked the review
    existing_like = db.execute('SELECT * FROM likes WHERE user_id=? AND review_id=?', user_id, review_id)
    if existing_like:
        # unlike the review
        db.execute('DELETE FROM likes WHERE user_id=? AND review_id=?', user_id, review_id)
        liked = False

    else:
        # like the review
        db.execute('INSERT INTO likes (user_id, review_id) VALUES(?,?)', user_id, review_id)
        liked = True

    results = db.execute('SELECT COUNT(*) AS total_likes FROM likes WHERE review_id=?', review_id)
    total_likes = results[0]['total_likes']

    return jsonify({"liked": liked, "total_likes": total_likes})


@app.route("/delete-review/<int:review_id>", methods=["GET"])
@login_required
def delete_review(review_id):
    """ allow users to delete their own reviews """

    user_id = session.get('user_id')

    # check if the review exists and belongs to the current user
    review = db.execute('SELECT * FROM reviews WHERE id=? AND user_id=?', review_id, user_id)

    if not review:
        return redirect("/account")

    # delete the review
    db.execute('DELETE FROM reviews WHERE id=?', review_id)

    return redirect("/account")

@app.route("/edit-review", methods=["POST"])
@login_required
def edit_review():
    """ allow users to edit their own reviews """

    user_id = session["user_id"]
    review_id = request.form.get("review_id")
    review_content = request.form.get("review")
    rating = int(request.form.get("rating"))
    print(f'edit info: {review_id}, {review_content}, {rating}')

    # check if the review exists and belongs to the current user
    review = db.execute('SELECT * FROM reviews WHERE id=? AND user_id=?', int(review_id), user_id)
    if not review:
        error = "Review not found or does not belong to user"
        return redirect("/account", message=error)

    if not rating or rating < 1 or rating > 5:
        error = 'Please provide a valid rating (1-5)'
        return redirect("/account", message=error)

    if not review_content:
        error = 'Please provide a review.'
        return redirect("/account", message=error)

    # update the review in the database
    db.execute('UPDATE reviews SET review_content=?, rating=? WHERE id=?', review_content, rating, review_id)
    message = 'Review added'
    return redirect(f"/account?message={message}")


@app.route("/user/<username>", methods=["GET"])
def other_user_profile(username):
    """ show a user's profile """

    # get the user's information
    user = db.execute('SELECT id, username FROM users WHERE username=?', username)
    if not user:
        return redirect("/")

    # if current user
    if session.get('user_id') == user[0]['id']:
        return redirect('/account')

    # get the user's reviews
    reviews = db.execute('SELECT reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist, COUNT(likes.id) AS total_likes FROM reviews LEFT JOIN likes ON likes.review_id = reviews.id WHERE reviews.user_id = ? GROUP BY reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist', user[0]['id'])
    for review in reviews:
        existing_likes = db.execute('SELECT * FROM likes WHERE user_id=? AND review_id=?', session["user_id"], review["id"])
        if existing_likes:
            review["liked"] = True
        else:
            review["liked"] = False


    return render_template("usersProfile.html", username=user[0]['username'], reviews=reviews)

@app.route('/forgot_password', methods=["GET"])
def forgot_password():
    """ direct user to the validate user email page """

    return render_template("resetPassword.html", emailConfirmed=False)

@app.route('/validateUseremail', methods=["POST"])
def validate_user():
    """ direct user to the reset password page """

    email = request.form.get('email')

    # get user details
    user_info = db.execute('SELECT * FROM users WHERE email=?', email)
    print(user_info)

    # user email not found in the db
    if not user_info:
        error = 'No user exists with that email'
        return render_template("resetPassword.html", emailConfirmed=False, message=error)

    # user email found in the db
    return render_template("resetPassword.html", emailConfirmed=True, user_id=user_info[0]['id'])


@app.route('/resetPassword', methods=["POST"])
def reset_Password():
    """ resent password """
    new_password = request.form.get('password')
    password_confirmation = request.form.get('confirmation')
    user_id = request.form.get('user_id')

    if not new_password:
        error = 'invalid password'
        return render_template("resetPassword.html", emailConfirmed=True, message=error)

    if not new_password == password_confirmation:
        error = 'password do not match'
        return render_template("resetPassword.html", emailConfirmed=True, message=error)

    #hash password
    hashed_password = generate_password_hash(new_password)

    # update password in the db
    db.execute('UPDATE users SET password_hash=? WHERE id=?', hashed_password, user_id)
    message = 'Password reset successful'
    return redirect(f'/login?message={message}')


@app.route('/newsLetter', methods=["POST"])
@login_required
def subscribe():
    """ add user to monthly newsletter """
    email = request.form.get('email')
    user_id = session['user_id']
    
    if not email:
        error = 'Please provide a valid email'
        return redirect(f'/?message={error}')

    # store email to database
    db.execute('INSERT INTO newsletter(user_id, email) VALUES(?,?)', user_id, email)
    message = 'Thank you for subscribing to the newsletter'
    return redirect(f'/?message={message}')
