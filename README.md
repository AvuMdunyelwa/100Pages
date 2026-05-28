# 🎵 100Pages — A Social Music Review Web App

youtube url: https://youtu.be/29VIxXx_GSw?si=Vlu8Mt4dBfEDegicC

100Pages is a full-stack web application that lets users discover, review, and rate songs. Built with Python (Flask) on the backend and a SQLite database, the app allows anyone to browse popular reviews and trending songs — but unlocks the full social experience (writing reviews, liking others' reviews, and managing a personal profile) once they register and log in. Think of it as a Letterboxd, but for music: a community-driven space where listeners can share their takes on tracks, discover what others are enjoying, and build a personal catalogue of their musical opinions.

The project was built as a final project for CS50x and represents the culmination of concepts covered throughout the course — including web routes, session management, database design, password security, and dynamic front-end interactivity.

---

## app.py

`app.py` is the heart of the application. It configures the Flask app, connects to the SQLite database via CS50's `SQL` helper, and defines every route the application supports. Sessions are managed via the filesystem (rather than signed cookies) to persist login state securely across requests. A custom `after_request` hook disables browser caching on all responses, ensuring users always see fresh data.

The routes cover the full user journey:

- **`/` (landing page / home feed):** The root route serves a dual purpose. If no user is logged in, it renders `index.html` — the public landing page — showing the top 5 highest-rated songs from the past 7 days and the 10 most-liked reviews. If a user session exists, the same query logic runs but additionally checks which reviews the logged-in user has already liked, injecting a `liked` boolean per review before rendering `homeFeed.html`. This dual-purpose design was a deliberate choice: rather than maintaining two separate routes for guests and logged-in users, a single route branches based on session state, keeping the URL clean and the logic centralised.

- **`/login` and `/register`:** Standard authentication routes. Registration hashes passwords using Werkzeug's `generate_password_hash` before storing them, and login verifies credentials with `check_password_hash`. Errors (mismatched passwords, duplicate usernames, missing fields) are passed back to the template as inline messages rather than flash alerts — a design decision made to keep feedback immediate and contextual without requiring a full page reload pattern.

- **`/logout`:** Clears the session and redirects to the landing page.

- **`/song`:** Accepts a POST request with a song search query, calls the external `search_for_song` function from `api.py`, and renders `music.html` with the results. If the search returns nothing, the user is sent back with an error message.

- **`/review`:** A login-protected POST route that takes track metadata (ID, title, artist, cover image) and the user's written review and rating, validates all fields, and inserts the review into the database. After a successful submission, the user is redirected to their profile page.

- **`/account`:** A login-protected GET route that fetches all reviews belonging to the logged-in user and renders them on `profile.html`.

- **`/reviews`:** A public route that displays all reviews ordered by most recent, along with the top 5 all-time rated songs and the top 5 most prolific reviewers. Like the home feed, it checks which reviews the current user has liked.

- **`/likes`:** A login-protected POST route that handles toggling likes on reviews. It checks whether a like already exists for the user/review pair — deleting it if so (unlike), or inserting a new one (like). It returns a JSON response with the updated like count and liked state, enabling the front-end JavaScript to update the UI without a full page reload.

---

## help.py

`help.py` contains the `login_required` decorator — a utility function that wraps protected routes and redirects unauthenticated users to the login page. Rather than duplicating session-check logic across every protected route, this decorator cleanly enforces authentication in a single reusable place. This is applied to `/logout`, `/review`, `/account`, and `/likes`.

---

## api.py

`api.py` contains the `search_for_song` function, which interfaces with an external music API (such as the Spotify API or a similar service) to search for tracks by title. It returns a list of song objects containing the track ID, title, artist name, and album cover image URL. Separating this into its own module was an intentional design choice — keeping API logic decoupled from route logic makes it easier to swap out or update the music data source without touching the core application.

---

## HTML Templates

### index.html — Landing Page
The public-facing landing page. It introduces the app to new visitors and showcases the most popular reviews and top-rated songs of the week without requiring a login. It includes calls to action for registering and logging in, designed to convert curious visitors into members.

### homeFeed.html — Home Feed
The authenticated user's home screen. It renders the same popular reviews and trending songs as the landing page, but with like buttons that reflect the current user's like state. The feed is personalised in that the app knows which reviews you've already liked and renders the heart/like icon accordingly.

### login.html — Login Page
A simple form collecting username and password. Inline error messages are rendered directly in the template when credentials are invalid or fields are missing, keeping the feedback loop tight.

### register.html — Registration Page
Collects username, email, password, and password confirmation. Validates on the server side and returns descriptive errors for each failure case.

### music.html — Song Search & Review Page
Displays search results from the music API. Each result shows the album cover, track title, and artist. Users can select a track and submit a written review with a star rating (1–5). The track metadata (ID, title, artist, cover URL) is passed as hidden form fields so the backend can store it alongside the review.

### profile.html — User Profile
Shows the logged-in user's personal review history — all the tracks they've reviewed, with their written content and ratings displayed. This serves as the user's musical diary.

### reviews.html — All Reviews
A community-wide feed of all reviews sorted by most recent. Also surfaces the top 5 all-time highest-rated songs and a leaderboard of the top 5 most active reviewers, encouraging community engagement.

---

## static/styles.css

The CSS file handles the visual design of the entire application — typography, colour palette, card layouts for reviews and song tiles, responsive behaviour, and the styling of like buttons and star ratings. A consistent dark or music-themed aesthetic was used across all pages to give the app a cohesive identity that fits the domain.

---

## static/script.js

The JavaScript file powers the like functionality without page reloads. When a user clicks a like button, a `fetch` POST request is sent to `/likes` with the review ID. The JSON response (containing the new like count and liked state) is used to update the button's appearance and the displayed count in real time. This was one of the more important design decisions in the project: submitting likes via a traditional form would cause a full page reload and scroll position loss, which feels jarring in a feed-style UI. Using `fetch` and JSON keeps the interaction smooth and modern.

---

## Database: music.db

The SQLite database contains three core tables:

- **`users`** — stores user ID, username, email, and hashed password.
- **`reviews`** — stores review ID, user ID (foreign key), track ID, song title, artist, cover image URL, review content, rating, and a `created_at` timestamp.
- **`likes`** — a join table storing user ID and review ID pairs, representing which users have liked which reviews.

The likes table uses a composite relationship that allows the app to toggle likes idempotently — checking for existence before inserting or deleting.

---

## Design Decisions Worth Noting

One deliberate trade-off was keeping the landing page and home feed as a single route (`/`) that branches on session state, rather than two separate URLs. This keeps the app's entry point clean and avoids redirect chains for logged-in users who navigate to the root.

Another considered choice was storing track metadata (title, artist, image) directly in the `reviews` table rather than maintaining a separate `tracks` table. This denormalises the data slightly but avoids the complexity of a tracks table that would need to sync with an external API — since the app doesn't own the music data, it makes more sense to snapshot it at review time.

Finally, the like system returning JSON instead of doing a redirect makes the feed feel responsive and alive — a small detail that meaningfully improves the user experience.
