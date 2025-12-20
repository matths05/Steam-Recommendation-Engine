URL: <https://steam-recommendation-engine.vercel.app/>
# Steam Recommendation Engine

A personalized game recommender system built with Flask. Users create an account, link a Steam profile (SteamID64 or vanity name), and sync their Steam library to import play history (hours played per game). The app provides (1) a tag-based recommender using the user’s favorite/hated tags and (2) a “People Like You” recommender using a K-Nearest Neighbors model with cosine similarity on tag-based taste vectors, recommending games similar users played that the current user doesn’t own or hasn’t pinned.

## Logged-In User Functionality

All core features require login. Logged-in users can sync a Steam library, set favorite and disliked tags (blacklist genres), pin games to a wishlist, manually rate games (by AppID or Steam store URL), and view similarity scores with other users (including a friend-compare tool).

## Forms

1. **Register / Login forms**: Account access.
2. **Steam Profile + Sync form**: Link SteamID and sync library.
3. **Preferences form**: Favorite/hated tags.
4. **Manual Rating form**: Rate/remove ratings.
5. **Friend Compare form**: Compute similarity with a Steam user

## Routes and Blueprints

**auth Blueprint**: `/register`, `/login`, `/logout`

**engine Blueprint**: ` /recommendations`, `/knn`, `/train_model`

**profile Blueprint**: ` /steam`, `/preferences`, `/rate`, `/friend_compare`

**explore Blueprint**: `/game/<appid>`, `/genre/<tag>`

## MongoDB Collections

**Users Collection**: SteamID, Owned_Games (Array of IDs + Hours), Favorite_tags, Hated_tags, Pinned_games, Last_sync.

**Games Collection**: AppID, Name, Tags, Global_Rating.

**Ratings**: User_id, AppID, Rating.

## Python Packages and APIs

**Package**: Scikit-Learn (for the KNN or Cosine Similarity algorithm).

**API**: Steam Web API / Store API (via requests) for import owned games/playtime and fetch game metadata
