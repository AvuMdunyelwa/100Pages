import os
from datetime import datetime, timezone
import timeago
import os
import psycopg2
import psycopg2.extras
from flask import *
from flask import Flask, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date
from help import login_required
from api import search_for_song
from supabase import create_client

# access supabase storage
supabase = create_client(
    os.environ.get('SUPABASE_URL'),
    os.environ.get('SUPABASE_KEY')
)

# Database helper — replaces CS50 SQL
def db_execute(query, **params):
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode='require')
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params)
    try:
        rows = cur.fetchall()
        result = [dict(row) for row in rows]
    except psycopg2.ProgrammingError:
        result = []
    cur.close()
    conn.close()
    return result


# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


def get_elapsed_time(timestamp, locale="en"):
    if not timestamp:
        return "unknown"

    if isinstance(timestamp, str):
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ]
        naive_date = None
        for fmt in formats:
            try:
                naive_date = datetime.strptime(timestamp, fmt)
                break
            except ValueError:
                continue
        if naive_date is None:
            return "unknown"
    else:
        naive_date = timestamp

    past_date = naive_date.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    try:
        return timeago.format(past_date, now, locale)
    except Exception:
        return timeago.format(past_date, now, "en")


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
    popular_songs = db_execute("SELECT track_id, MAX(cover_img_url) AS cover_img_url, AVG(rating) AS average_rating, COUNT(*) AS review_count FROM reviews WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY track_id ORDER BY review_count DESC, AVG(rating) DESC LIMIT 5")
    reviews = db_execute("SELECT reviews.id AS review_id, reviews.song_title, reviews.artist, reviews.review_content, reviews.rating, reviews.cover_img_url, users.username, users.profile_img AS profile_pic, COUNT(likes.review_id) AS total_likes FROM reviews JOIN users ON users.id = reviews.user_id LEFT JOIN likes ON reviews.id = likes.review_id GROUP BY reviews.id, reviews.song_title, reviews.artist, reviews.review_content, reviews.rating, reviews.cover_img_url, users.username, users.profile_img ORDER BY total_likes DESC LIMIT 10")

    if session.get('user_id'):
        user_id = session['user_id']
        username = db_execute("SELECT username FROM users WHERE id=%(id)s", id=user_id)
        for review in reviews:
            existing_likes = db_execute("SELECT * FROM likes WHERE user_id=%(uid)s AND review_id=%(rid)s", uid=session["user_id"], rid=review["review_id"])
            review["liked"] = bool(existing_likes)
        return render_template('homeFeed.html', username=username[0]['username'], reviews=reviews, popular_songs=popular_songs, message=message)

    return render_template('index.html', reviews=reviews, popular_songs=popular_songs)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")


@app.route('/login', methods=['POST', 'GET'])
def login():
    message = request.args.get('message')
    session.clear()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username:
            return render_template("login.html", message='Enter valid username')
        elif not password:
            return render_template("login.html", message='Enter valid password')

        rows = db_execute("SELECT * FROM users WHERE username=%(username)s", username=username)

        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], password):
            return render_template("login.html", message='Invalid username and/or password')

        session["user_id"] = rows[0]["id"]
        message = 'Successfully login!'
        return redirect(f'/?message={message}')
    else:
        return render_template("login.html", message=message)


@app.route("/register", methods=["GET", "POST"])
def register():
    """ register newcomers """

    if request.method == 'POST':
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')
        email = request.form.get('email')
        username = request.form.get('username')
        name = request.form.get('name')
        surname = request.form.get('surname')

        if not username:
            return render_template("register.html", message='Invalid username')
        if not name or not surname:
            return render_template("register.html", message='Invalid name or surname')
        if not email:
            return render_template("register.html", message='Invalid email')
        if not password or password != confirmation:
            return render_template("register.html", message='Passwords do not match')

        try:
            db_execute("INSERT INTO users (username, name, surname, email, password_hash) VALUES(%(username)s, %(name)s, %(surname)s, %(email)s, %(password_hash)s)",
                       username=username, name=name, surname=surname, email=email, password_hash=generate_password_hash(password))
            message = 'Login successful!'
            return redirect(f'/login?message={message}')
        
        except Exception:
            return render_template("register.html", message='Username or email already exists')
    else:
        return render_template('register.html')


@app.route("/song", methods=["POST"])
def find_track():
    """ return search results of a song """

    song = request.form.get("song")
    artist = request.form.get("artist")

    if not song:
        return render_template("music.html", message="Please enter a song title")

    songs = search_for_song(song, artist)

    if not songs:
        return render_template("music.html", message=f"No results found for: {song}")

    try:
        return render_template("music.html", songs=songs, input=song)
    except ValueError:
        return render_template("music.html", message=f"No results found for: {song}")


@app.route("/review", methods=["POST"])
@login_required
def store_review():
    """ store review post details """

    user_id = session["user_id"]
    track_id = request.form.get("id")
    track_title = request.form.get("title")
    track_artist = request.form.get("artist")
    track_img = request.form.get("img")
    review = request.form.get("review")
    rating = request.form.get("rating")

    if not rating or int(rating) < 1 or int(rating) > 5:
        return render_template("music.html", message='Please provide a valid rating (1-5)')
    if not track_id or not track_title or not track_artist or not track_img:
        return render_template("music.html", message='Invalid track information. Please try again.')
    if not review:
        return render_template("music.html", message='Please provide a review.')

    existing_review = db_execute('SELECT * FROM reviews WHERE user_id=%(user_id)s AND track_id=%(track_id)s', user_id=user_id, track_id=track_id)
    if existing_review:
        return render_template('music.html', message='You have already reviewed this song')
    
    db_execute("INSERT INTO reviews (user_id, track_id, song_title, artist, cover_img_url, review_content, rating) VALUES(%(user_id)s, %(track_id)s, %(song_title)s, %(artist)s, %(cover_img_url)s, %(review_content)s, %(rating)s)",
               user_id=user_id, track_id=track_id, song_title=track_title, artist=track_artist, cover_img_url=track_img, review_content=review, rating=rating)

    #get added review id
    review_id = db_execute('SELECT * FROM reviews WHERE user_id=%(user_id)s AND track_id=%(track_id)s', user_id=user_id, track_id=track_id)

    notify_review = db_execute('INSERT INTO notifications (recipient_id, sender_id, type, review_id, is_read) VALUES(%(recipient_id)s, %(sender_id)s, %(type)s, %(review_id)s, %(is_read)s)', 
                               recipient_id=user_id, sender_id=user_id, type='added_review', review_id=review_id[0]['id'], is_read=False)
    
 
    return redirect(f"/account?message=review successfully added!")


@app.route("/account", methods=["GET"])
@login_required
def profile():
    """ get users reviews """
    message = request.args.get('message')
    user_id = session["user_id"]
    userstats = db_execute("SELECT COUNT(DISTINCT reviews.id) AS total_reviews, COUNT(likes.id) AS total_likes, users.username AS username, users.profile_img AS profile_pic, users.id, users.name, users.surname, users.email FROM reviews JOIN users ON users.id = reviews.user_id LEFT JOIN likes ON likes.review_id = reviews.id WHERE reviews.user_id = %(user_id)s GROUP BY users.id, users.username, users.id, users.name, users.surname, users.email", user_id=user_id)
    print(userstats)
    reviews = db_execute("SELECT reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist, COUNT(likes.id) AS total_likes FROM reviews LEFT JOIN likes ON likes.review_id = reviews.id WHERE reviews.user_id = %(user_id)s GROUP BY reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist;", user_id=user_id)
    return render_template("profile.html", reviews=reviews, userstats=userstats, message=message)


@app.route("/reviews", methods=["GET"])
def reviews():
    """ get all reviews """

    popular_songs = db_execute("SELECT track_id, MAX(cover_img_url) AS cover_img_url, AVG(rating) AS average_rating FROM reviews GROUP BY track_id ORDER BY AVG(rating) DESC LIMIT 5")
    reviews = db_execute("SELECT reviews.id AS review_id, reviews.song_title, reviews.artist, reviews.review_content, reviews.rating, reviews.cover_img_url, users.username, users.profile_img AS profile_pic, COUNT(likes.review_id) AS total_likes, MAX(reviews.created_at) AS created_at FROM reviews JOIN users ON users.id = reviews.user_id LEFT JOIN likes ON reviews.id = likes.review_id GROUP BY reviews.id, reviews.song_title, reviews.artist, reviews.review_content, reviews.rating, reviews.cover_img_url, users.username, users.profile_img ORDER BY created_at DESC LIMIT 10")

    for review in reviews:
        if session.get('user_id'):
            existing_likes = db_execute("SELECT * FROM likes WHERE user_id=%(uid)s AND review_id=%(rid)s", uid=session["user_id"], rid=review["review_id"])
            review["liked"] = bool(existing_likes)
        else:
            review["liked"] = False

    top_reviewers = db_execute("SELECT username, COUNT(reviews.id) AS review_count, profile_img AS profile_pic FROM users JOIN reviews ON reviews.user_id = users.id GROUP BY users.id, users.username, users.profile_img ORDER BY COUNT(reviews.id) DESC LIMIT 5")

    return render_template("reviews.html", reviews=reviews, popular_songs=popular_songs, top_reviewers=top_reviewers)


@app.route("/likes", methods=["POST"])
@login_required
def like_review():
    """ record review posts liked """

    review_id = int(request.form.get("review_id"))
    user_id = session["user_id"]

    if not review_id:
        return redirect("/reviews")

    #check for reviews liked by user
    existing_like = db_execute("SELECT * FROM likes WHERE user_id=%(uid)s AND review_id=%(rid)s", uid=user_id, rid=review_id)

    if existing_like:
        db_execute("DELETE FROM likes WHERE user_id=%(uid)s AND review_id=%(rid)s", uid=user_id, rid=review_id)
        liked = False
    else:
        db_execute("INSERT INTO likes (user_id, review_id) VALUES(%(user_id)s, %(review_id)s)", user_id=user_id, review_id=review_id)
        liked = True

    #record like notification
    recipient_id = db_execute('SELECT * FROM reviews WHERE id=%(review_id)s', review_id=review_id)

    # notify the liker that they liked a review
    db_execute('INSERT INTO notifications (recipient_id, sender_id, type, review_id, is_read) VALUES(%(recipient_id)s, %(sender_id)s, %(type)s, %(review_id)s, %(is_read)s)',
        recipient_id=user_id, sender_id=user_id, type='liked_review', review_id=review_id, is_read=False)
    
    if not recipient_id[0]['user_id'] == user_id:
        # notify the review owner that their review was liked
        db_execute('INSERT INTO notifications (recipient_id, sender_id, type, review_id, is_read) VALUES(%(recipient_id)s, %(sender_id)s, %(type)s, %(review_id)s, %(is_read)s)',
                recipient_id=recipient_id[0]['user_id'], sender_id=user_id, type='received_like', review_id=review_id, is_read=False)

    results = db_execute("SELECT COUNT(*) AS total_likes FROM likes WHERE review_id=%(rid)s", rid=review_id)
    total_likes = results[0]['total_likes']

    return jsonify({"liked": liked, "total_likes": total_likes})


@app.route("/delete-review/<int:review_id>", methods=["GET"])
@login_required
def delete_review(review_id):
    """ edit users review post """

    user_id = session.get('user_id')
    review = db_execute("SELECT * FROM reviews WHERE id=%(id)s AND user_id=%(user_id)s", id=review_id, user_id=user_id)

    if not review:
        return redirect("/account")

    db_execute("DELETE FROM reviews WHERE id=%(id)s", id=review_id)
    return redirect("/account?message=Review deleted")


@app.route("/edit-review", methods=["POST"])
@login_required
def edit_review():
    """ edit users review post """

    user_id = session["user_id"]
    review_id = request.form.get("review_id")
    review_content = request.form.get("review")
    rating = int(request.form.get("rating"))

    review = db_execute("SELECT * FROM reviews WHERE id=%(id)s AND user_id=%(user_id)s", id=int(review_id), user_id=user_id)
    if not review:
        return redirect("/account")
    if not rating or rating < 1 or rating > 5:
        return redirect("/account")
    if not review_content:
        return redirect("/account")

    db_execute("UPDATE reviews SET review_content=%(review_content)s, rating=%(rating)s WHERE id=%(id)s", review_content=review_content, rating=rating, id=review_id)
    return redirect("/account?message=Review updated")


@app.route("/user/<username>", methods=["GET"])
def other_user_profile(username):
    """ view other users profiles """

    print('this is the username: ', username)

    user = db_execute("SELECT id, username FROM users WHERE username=%(username)s", username=username)
    if not user:
        return redirect("/")

    if session.get('user_id') == user[0]['id']:
        return redirect('/account')

    reviews = db_execute("SELECT reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist, COUNT(likes.id) AS total_likes FROM reviews LEFT JOIN likes ON likes.review_id = reviews.id WHERE reviews.user_id=%(user_id)s GROUP BY reviews.id, reviews.review_content, reviews.rating, reviews.cover_img_url, reviews.song_title, reviews.artist", user_id=user[0]['id'])
    for review in reviews:
        if session.get('user_id'):
            existing_likes = db_execute("SELECT * FROM likes WHERE user_id=%(uid)s AND review_id=%(rid)s", uid=session["user_id"], rid=review["id"])
            review["liked"] = bool(existing_likes)
        else:
            review["liked"] = False

    return render_template("usersProfile.html", username=user[0]['username'], reviews=reviews)


@app.route('/forgot_password', methods=["GET"])
def forgot_password():
    return render_template("resetPassword.html", emailConfirmed=False)


@app.route('/validateUseremail', methods=["POST"])
def validate_user():
    """ check user exist through email check before allowing password reset """

    email = request.form.get('email')
    user_info = db_execute("SELECT * FROM users WHERE email=%(email)s", email=email)

    if not user_info:
        return render_template("resetPassword.html", emailConfirmed=False, message='No user exists with that email')

    return render_template("resetPassword.html", emailConfirmed=True, user_id=user_info[0]['id'])


@app.route('/resetPassword', methods=["POST"])
def reset_Password():
    """ reset users existing password """

    new_password = request.form.get('password')
    password_confirmation = request.form.get('confirmation')
    user_id = request.form.get('user_id')

    if not new_password:
        return render_template("resetPassword.html", emailConfirmed=True, message='Invalid password')
    if new_password != password_confirmation:
        return render_template("resetPassword.html", emailConfirmed=True, message='Passwords do not match')

    hashed_password = generate_password_hash(new_password)
    db_execute("UPDATE users SET password_hash=%(password_hash)s WHERE id=%(id)s", password_hash=hashed_password, id=user_id)
    return redirect("/login?message='Password reset successful'")


@app.route('/newsLetter', methods=["POST"])
@login_required
def subscribe():
    email = request.form.get('email')
    user_id = session['user_id']

    if not email:
        return redirect('/?message=Please provide a valid email')

    db_execute("INSERT INTO newsletter(user_id, email) VALUES(%(user_id)s, %(email)s)", user_id=user_id, email=email)
    return redirect('/?message=Thank you for subscribing to the newsletter')

@app.route('/activity', methods=["GET"])
@login_required
def get_activity():
    """ get users notifications """
    user_id = session.get('user_id')

    # get all user's notifications
    notifications = db_execute('SELECT notifications.*, sender.username AS sender, owner.username AS owner, reviews.artist, reviews.song_title, reviews.cover_img_url AS cover FROM notifications JOIN users AS sender ON sender.id = notifications.sender_id JOIN reviews ON reviews.id = notifications.review_id JOIN users AS owner ON owner.id = reviews.user_id WHERE recipient_id=%(user_id)s ORDER BY notifications.created_at DESC', user_id=user_id)

    for activity in notifications:
        activity['created_at'] = get_elapsed_time(activity['created_at']) 
        db_execute('UPDATE notifications SET is_read=%(read)s WHERE id=%(id)s', read="True", id=activity['id'])

    return render_template('notifications.html', notifications=notifications)
   
@app.route('/store-pp', methods=["POST"])
@login_required
def store_profile_pic():
    """ store the users profile picture """

    print('route reached!')
    user_id = session.get('user_id')
    img_file = request.files.get('addprofile')
    imgBytes = img_file.read()

    if not imgBytes:
        return redirect(url_for('account', message='upload a valid image file'))
    
    filename = f'{user_id}-pp'
    img_path = f"profile-pics/{user_id}/{filename}"

    # store image to the storage
    upload = supabase.storage.from_('100Pages-storage').upload(img_path, imgBytes, {'upsert': 'true', 'content-type': img_file.mimetype})
    print('is it uploaded: ', upload)
    if upload:
        img_url = supabase.storage.from_('100Pages-storage').get_public_url(img_path)
        db_execute('UPDATE users SET profile_img = %(url)s WHERE id = %(id)s', url=img_url, id=user_id)
        return redirect('/account')
    else:
        return redirect(url_for('profile', message='image failed to upload'))


@app.route("/edit-profile", methods=["POST"])
@login_required
def edit_profile():
    """ update users details """

    user_id = session["user_id"]
    user_name = request.form.get("name")
    user_surname = request.form.get("surname")
    user_username = request.form.get("username")
    user_email = request.form.get("email")
    print('user-details: ', user_id, user_name, user_surname, user_username, user_email)
    user_details = db_execute("SELECT * FROM users WHERE id=%(user_id)s", user_id=user_id)
    print('current user details: ', user_details)
    if not user_details:
        return redirect("/account")
    
    if not user_name or user_surname or user_username or user_email :
        return redirect("/account")

    db_execute("UPDATE users SET name=%(name)s, surname=%(surname)s, username=%(username)%, email=%(email)% WHERE id=%(id)s", name=user_name, surname=user_surname, username=user_username, email=user_email, id=user_id)
    return redirect(f"/account?message=Details updated")