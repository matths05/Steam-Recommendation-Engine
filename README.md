# Steam Recommendation Engine

A personalized game recommender system. Users log in via Steam, and the app imports their entire play history (hours played per game). It uses a K-Nearest Neighbors (KNN) algorithm to find other games in the database with similar categories, and suggests games they played that you haven't and are highly rated.

## Logged-In User Functionality

The entire app revolves around the logged-in user's data. They can blacklist genres (e.g., "Never show me Horror"), "Pin" recommendations to a wishlist, and view a "Similarity Score" with other users.

## Forms

1. **Sync Form**: Button to trigger a re-sync of the Steam Library.
2. **Preference Form**: Checkboxes for "Favorite Tags" and "Hated Tags."
3. **Manual Rate Form**: A form to give a 1-10 rating to a game (overriding the "Hours Played" metric).
4. **Friend Compare**: Input a friend's Steam ID to see compatibility.

## Routes and Blueprints

**engine Blueprint**: `/train_model`, `/get_recommendations`

**profile Blueprint**: `/sync_steam`, `/preferences`

**explore Blueprint**: `/game/<id>`, `/genre/<tag>`

## MongoDB Collections

**Users Collection**: SteamID, Owned_Games (Array of IDs + Hours), Calculated_Vector (Math representation of taste).

**Games Collection**: AppID, Name, Tags, Global_Rating.

## Python Packages and APIs

**Package**: Scikit-Learn (for the KNN or Cosine Similarity algorithm).
