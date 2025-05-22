from flask import Flask, render_template, session, redirect, request, url_for, jsonify
from joblib import load
import requests
import json
import base64
import os
import pandas as pd
import difflib

app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = "85c8678f0843408890708001d9c081bc"
CLIENT_SECRET = "f7560a2e8d8d4e79987fcde27fb86add"
REDIRECT_URI = "http://127.0.0.1:5000/callback"

# Load artist model once
df_artist = pd.DataFrame(load("data/model/artist/data.pkl"))

df_artist_info = pd.read_csv("data/model/artist/artists_list_with_bio.csv")
artist_info_dict = {
    row["key"]: {
        "name": row["Artist Name"],
        "bio": (row["bio"].strip().rstrip('.') + "... (wikipedia)") if not row["bio"].strip().endswith("(wikipedia)") else row["bio"],
        "image": row["Image URL"]
    }
    for _, row in df_artist_info.iterrows()
}

## Untuk Top Artis lebih dari 7K data
# artist_info_dict = {
#     row["key"]: {
#         "name": row["artist"],
#         "bio": (
#             (row["bio"].strip().rstrip('.') + "... (wikipedia)")
#             if pd.notnull(row["bio"]) and not row["bio"].strip().endswith("(wikipedia)")
#             else (row["bio"] if pd.notnull(row["bio"]) else "No biography available.")
#         ),
#         "image": row["Image URL"]
#     }
#     for _, row in df_artist_info.iterrows()
# }


# Spotify Client Credentials Token
def get_client_token():
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {"grant_type": "client_credentials"}

    response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    return response.json()["access_token"]

# Authorization Code Token (user login)
def get_user_token(code):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
    return response.json()

# Convert ms to min:sec
def millis_to_time(ms):
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    return f"{minutes}:{seconds:02}"

@app.route("/login")
def login():
    scope = "user-library-read playlist-read-private user-read-private"
    return redirect(
        f"https://accounts.spotify.com/authorize?client_id={CLIENT_ID}&response_type=code"
        f"&redirect_uri={REDIRECT_URI}&scope={scope}"
    )

@app.route("/callback")
def callback():
    code = request.args.get("code")
    token_info = get_user_token(code)

    if "access_token" not in token_info:
        return "Login failed. Please try again.", 400

    # Simpan access token ke session
    session["access_token"] = token_info.get("access_token")

    # Ambil profil user dari Spotify
    access_token = session["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_resp = requests.get("https://api.spotify.com/v1/me", headers=headers)

    if user_resp.status_code == 200:
        user_data = user_resp.json()
        session["user_name"] = user_data.get("display_name", "Unknown User")
        session["user_type"] = user_data.get("product", "Free").capitalize() + " Member"

        images = user_data.get("images", [])
        session["user_image"] = images[0]["url"] if images else ""
    else:
        session["user_name"] = "Unknown User"
        session["user_type"] = "Free Member"
        session["user_image"] = ""

    return redirect(url_for("index"))

def get_top_artist_from_chart_json():
    with open("data/charts.json", "r") as f:
        charts_data = json.load(f)
    try:
        chart = charts_data["chartEntryViewResponses"][0]
        first_entry = chart["entries"][0]
        meta = first_entry["trackMetadata"]
        artist = meta["artists"][0]
        artist_id = artist["spotifyUri"].split(":")[-1]
        name = artist["name"]
        image = meta.get("displayImageUri", "")
        return {
            "name": name,
            "spotify_url": f"https://open.spotify.com/artist/{artist_id}",
            "image": image or "https://via.placeholder.com/600x300",
        }
    except Exception as e:
        print("[ERROR] Trending artist error:", e)
        return {
            "name": "Unknown Artist",
            "spotify_url": "#",
            "image": "https://via.placeholder.com/600x300",
        }

@app.route("/")
def index():
    if "access_token" not in session:
        return redirect(url_for("login"))

    try:
        data = load('data/model/genre/data_by_genre.pkl')
        genre_list = data['track_genre'].unique().tolist()
    except:
        genre_list = []

    trending_artist = get_top_artist_from_chart_json()
    playlist_tracks = []

    access_token = session.get("access_token")
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        playlists_resp = requests.get("https://api.spotify.com/v1/me/playlists", headers=headers)
        if playlists_resp.status_code == 200:
            playlists = playlists_resp.json().get("items", [])
            if playlists:
                playlist_id = playlists[0]["id"]
                first_playlist_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50"

                next_url = first_playlist_url
                while next_url:
                    resp = requests.get(next_url, headers=headers)
                    if resp.status_code != 200:
                        break
                    track_data = resp.json()
                    for item in track_data.get("items", []):
                        track = item.get("track")
                        if track:
                            playlist_tracks.append({
                                "title": track.get("name"),
                                "artist": ', '.join(artist["name"] for artist in track.get("artists", [])),
                                "album": track.get("album", {}).get("name"),
                                "duration": millis_to_time(track.get("duration_ms", 0))
                            })
                    next_url = track_data.get("next")

    return render_template("index.html", genres=genre_list, trending=trending_artist, playlist_tracks=playlist_tracks)

@app.route("/genresong")
def genresong():
    try:
        data = load('data/model/genre/data_by_genre.pkl')
        genre_list = data['track_genre'].unique().tolist()
    except:
        genre_list = []
    return render_template("genre-song.html", genres=genre_list)

@app.route("/genre/<genre_name>")
def genre_detail(genre_name):
    # Load genre descriptions once
    genre_descriptions = pd.read_csv("data/model/genre/description.csv")
    genre_descriptions["genre_key"] = genre_descriptions["genre"].str.strip().str.lower().str.replace(" ", "-")
    genre_description_dict = {
        row["genre_key"]: {
            "name": row["genre"],
            "bio": row["description"]
        }
        for _, row in genre_descriptions.iterrows()
    }

    # Normalisasi genre key
    genre_key = genre_name.strip().lower().replace(" ", "-")
    genre_meta = genre_description_dict.get(
        genre_key, {"name": genre_name, "bio": "No description available for this genre."}
    )

    try:
        # Load data dan model
        df = pd.read_pickle('data/model/genre/data_by_genre.pkl')
        scaler = load('data/model/genre/scaler_by_genre.pkl')
        model = load('data/model/genre/logreg_model_by_genre.pkl')
        features = load('data/model/genre/scaled_features_by_genre.pkl')  # bentuk: np.array

        # Prediksi semua genre
        predicted_genres = model.predict(features)
        print("Contoh prediksi genre dari model:", predicted_genres[:5])
        print("Genre yang dicari:", genre_name)

        # Gabungkan hasil prediksi ke dataframe
        df = df.reset_index(drop=True)
        df["predicted_genre"] = predicted_genres

        # Filter berdasarkan genre hasil prediksi
        recommended = df[df["predicted_genre"] == genre_name].sort_values(by="popularity", ascending=False).head(10)

        songs = recommended[["track_name", "artists", "popularity"]].to_dict(orient="records")

        return render_template("genre-detail.html", songs=songs, genre=genre_name, genre_meta=genre_meta)

    except Exception as e:
        print("[ERROR - genre_detail]", e)
        return render_template("genre-detail.html", songs=[], genre=genre_name, genre_meta=genre_meta)

@app.route("/popular")
def popular():
    try:
        df = pd.read_csv("data/model/artist/top_songs.csv")
        df = df.sort_values(by="popularity", ascending=False).head(5)

        def convert_duration(seconds):
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            return f"{minutes}:{secs:02}"

        if 'duration_s' in df.columns:
            df["duration"] = df["duration_s"].apply(convert_duration)
        else:
            df["duration"] = "N/A"

        # Hardcode file audio
        audio_files = [
            "Unholy_(ft. Kim Petras).mp3",
            "La_Bachata.mp3",
            "I'm_Good_(Blue).mp3",
            "Tití_Me_Preguntó.mp3",
            "Me_Porto_Bonito.mp3"
        ]

        # Hardcode image untuk background hero section
        image_urls = [
            "unholy.png",  # Unholy
            "la_bachata.jpg",  # La Bachata
            "3.jpeg",  # I'm Good
            "4.jpg",  # Tití Me Preguntó
            "5.jpeg",  # Me Porto Bonito
        ]

        top_songs = []
        for i, (_, row) in enumerate(df.iterrows()):
            audio = url_for('static', filename=f"assets/music/{audio_files[i]}") if i < len(audio_files) else "#"
            image = url_for('static', filename=f"assets/images/{image_urls[i]}") if i < len(image_urls) else url_for('static', filename='assets/images/no-image.jpg')
            top_songs.append({
                "title": row["track_name"],
                "artist": ", ".join(eval(row["artists"])) if isinstance(row["artists"], str) and row["artists"].startswith("[") else row["artists"],
                "duration": row["duration"],
                "image": image,
                "audio": audio
            })

        return render_template("popular.html", songs=top_songs)

    except Exception as e:
        print("[ERROR] Failed to load top_songs.csv:", e)
        return render_template("popular.html", songs=[])

@app.route("/artists")
def artists():
    result = [
        {
            "key": k,
            "name": v["name"],
            "image": v.get("image", "https://via.placeholder.com/160")
        }
        for k, v in artist_info_dict.items()
    ]
    return render_template("artists.html", artists=result)

@app.route("/api/artists")
def api_artists():
    try:
        page = int(request.args.get("page", 1))
        per_page = 28
        start = (page - 1) * per_page
        end = start + per_page

        all_artists = []
        for k, v in artist_info_dict.items():
            image_url = v.get("image")

            # Cek jika kosong, NaN, None, atau bukan string valid
            if not isinstance(image_url, str) or not image_url.strip() or image_url.lower() == "nan":
                image_url = url_for('static', filename='assets/images/no-image.jpg')

            all_artists.append({
                "key": k,
                "name": v["name"],
                "image": image_url
            })

        return jsonify(all_artists[start:end])

    except Exception as e:
        print("[ERROR]", e)
        return jsonify({"error": str(e)}), 500


@app.route("/artist/<key>")
def artist_page(key):
    artist = artist_info_dict.get(key)
    if not artist:
        return "Artist not found", 404

    matched = df_artist[df_artist["artists"].apply(
        lambda x: isinstance(x, list) and artist["name"].lower() in [a.lower() for a in x]
    )]
    songs = matched[["track_name", "popularity"]].sort_values(by="popularity", ascending=False).head(10).to_dict(orient="records")

    return render_template("artist_detail.html", artist=artist, songs=songs)

@app.route("/api/artist_detail/<key>")
def api_artist_detail(key):
    return jsonify(artist_info_dict.get(key, {}))


@app.route("/api/artist_tracks/<artist_name>")
def api_artist_tracks(artist_name):
    matched = df_artist[df_artist["artists"].apply(
        lambda x: isinstance(x, list) and artist_name.lower() in [a.lower() for a in x]
    )]
    
    result = matched[["track_name", "popularity"]].sort_values(
        by="popularity", ascending=False
    ).head(10)

    # Tambahkan kolom spotify_url kosong supaya tidak error di frontend
    result["spotify_url"] = None

    return result.to_json(orient="records")


@app.route("/discovery")
def discovery():
    with open("data/charts.json", "r") as f:
        charts_data = json.load(f)

    chart = charts_data["chartEntryViewResponses"][0]
    entries = chart["entries"]

    tracks = []
    for item in entries:
        meta = item["trackMetadata"]
        tracks.append({
            "rank": item["chartEntryData"]["currentRank"],
            "title": meta["trackName"],
            "artist": ', '.join(artist["name"] for artist in meta["artists"]),
            "image": meta["displayImageUri"],
            "spotify_url": f"https://open.spotify.com/track/{meta['trackUri'].split(':')[-1]}"
        })

    return render_template("discovery.html", tracks=tracks)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return render_template("search_result.html", query="", artists=[], songs=[], genres=[], suggested_genre=None, suggested_artist=None)

    # Pisahkan query menjadi frasa berdasarkan koma
    phrases = [p.strip() for p in query.split(",") if p.strip()]

    # Load data
    df = pd.read_pickle('data/model/genre/data_by_genre.pkl')
    artists_df = df_artist_info
    genre_descriptions = pd.read_csv("data/model/genre/description.csv")
    genre_descriptions["genre_key"] = genre_descriptions["genre"].str.lower().str.replace(" ", "-")

    # === CARI ARTISTS ===
    matched_artists = [
        {
            "key": row["key"],
            "name": row["Artist Name"],
            "image": row["Image URL"] if pd.notnull(row["Image URL"]) else url_for('static', filename='assets/images/no-image.jpg')
        }
        for _, row in artists_df.iterrows()
        if any(phrase in row["Artist Name"].lower() for phrase in phrases)
    ]

    # === CARI SONGS ===
    matched_songs = df[
        df["track_name"].str.lower().apply(lambda title: any(phrase in title for phrase in phrases))
    ][["track_name", "artists", "track_genre", "popularity"]].sort_values(
        by="popularity", ascending=False
    ).head(10).to_dict(orient="records")

    # === CARI GENRES ===
    matched_genres = genre_descriptions[
        genre_descriptions["genre"].str.lower().apply(lambda g: any(phrase in g for phrase in phrases))
    ][["genre", "description"]].to_dict(orient="records")

    # === SUGGESTED GENRE ===
    suggested_genre = None
    if not matched_genres:
        all_genres = genre_descriptions["genre"].str.lower().tolist()
        for phrase in phrases:
            close_matches = difflib.get_close_matches(phrase, all_genres, n=1, cutoff=0.7)
            if close_matches:
                match = close_matches[0]
                row = genre_descriptions[genre_descriptions["genre"].str.lower() == match].iloc[0]
                suggested_genre = {
                    "genre": row["genre"],
                    "description": row["description"]
                }
                break  # cukup 1 saran genre

    # === SUGGESTED ARTIST ===
    suggested_artist = None
    if not matched_artists:
        all_artists = artists_df["Artist Name"].str.lower().tolist()
        for phrase in phrases:
            close_matches = difflib.get_close_matches(phrase, all_artists, n=1, cutoff=0.7)
            if close_matches:
                match = close_matches[0]
                row = artists_df[artists_df["Artist Name"].str.lower() == match].iloc[0]
                suggested_artist = {
                    "key": row["key"],
                    "name": row["Artist Name"],
                    "image": row["Image URL"] if pd.notnull(row["Image URL"]) else url_for('static', filename='assets/images/no-image.jpg')
                }
                break  # cukup 1 saran artis

    # === RENDER KE HALAMAN ===
    return render_template(
        "search_result.html",
        query=query,
        artists=matched_artists,
        songs=matched_songs,
        genres=matched_genres,
        suggested_genre=suggested_genre,
        suggested_artist=suggested_artist
    )

if __name__ == "__main__":
    app.run(debug=True)