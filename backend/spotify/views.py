"""
Define the Views for the Spotfiy App. These contain the backend logic for each API in the Spotify App.

NOTE: A user is identified by their Session Key.
"""

from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
import requests
from .util import *
import base64
from api.models import Room
from .models import Vote
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load the environment variables
env = environ.Env(
    SPOTIFY_CLIENT_ID=(str),
    SPOTIFY_CLIENT_SECRET=(str),
    SPOTIFY_REDIRECT_URI=(str),
    FRONTEND_ENDPOINT=(str),
)

env_path = BASE_DIR / ".env"
if env_path.is_file():
    environ.Env.read_env(env_file=str(env_path))


class AuthURL(APIView):
    """
    [Step 1] Create the URL to return to the user to request authorization
    from the user so that the App can access Spotify resources on behalf of that user.
    """

    def get(self, request, format=None):
        """
        [Step 1] Create the URL to return to the user to request authorization
        from the user so that the App can access Spotify resources on behalf of that user.

        Request Body:
        client_id: The Client ID generated after registering your application.
        response_type: Set to code.
        redirect_uri: The URI to redirect to after the user grants or denies permission.
        scope:  A space-separated list of scopes. If no scopes are specified,
            authorization will be granted only to access publicly available information:
            that is, only information normally visible in the Spotify desktop, web,
            and mobile players.
        """
        # Permissions requested from the user and required for the App
        scopes = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

        # Request Body
        params = {
            "scope": scopes,
            "response_type": "code",
            "redirect_uri": env("SPOTIFY_REDIRECT_URI"),
            "client_id": env("SPOTIFY_CLIENT_ID"),
        }

        # Create Authorization URL
        url = (
            requests.Request(
                "GET", "https://accounts.spotify.com/authorize", params=params
            )
            .prepare()
            .url
        )

        return Response({"url": url}, status=status.HTTP_200_OK)


def spotify_callback(request, format=None):
    """
    [Step 2] Callback function invoked by Spotify to request an Access Token.

    Once a User has authorized the App to access Spotify resources on their behalf,
    the App can exchange the Authorization code for an Access Token.

    This function is invoked automatically after the User authorizes the App
    because Spotfiy uses the REDIRECT_URI specified to redirect them to this endpoint.
    """
    # Read the request body
    code = request.GET.get("code")
    # Optional: Read the error code to handle an error if there was one
    error = request.GET.get("error")

    # Define the Access Token request headers
    auth_header_string_bytes = (
        env("SPOTIFY_CLIENT_ID") + ":" + env("SPOTIFY_CLIENT_SECRET")
    ).encode("ascii")
    base64_bytes = base64.b64encode(auth_header_string_bytes)
    base64_string = base64_bytes.decode("ascii")
    headers = {"Authorization": f"Basic {base64_string}"}

    # Define the Access Token request body
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": env("SPOTIFY_REDIRECT_URI"),
    }

    # Request an Access Token
    response = requests.post(
        "https://accounts.spotify.com/api/token", headers=headers, data=data
    )

    # Extract fields from response body
    response = response.json()
    access_token = response.get("access_token")
    token_type = response.get("token_type")
    refresh_token = response.get("refresh_token")
    expires_in = response.get("expires_in")
    error = response.get("error")

    # Create a Session for the user if one does not exist already
    if not request.session.exists(request.session.session_key):
        request.session.create()

    # Create or Update the SpotifyToken and persist it in the database
    update_or_create_user_tokens(
        request.session.session_key, access_token, token_type, expires_in, refresh_token
    )

    # TODO: Currently redirects the user back to this url
    # Since we don't have the Room Code we can't go to that page. Technically
    # we could invoke the /api/user-in-room endpoint to get the room to redirect to
    # This endpoint needs to be updated based on where/how this is being hosted.
    return redirect(env("FRONTEND_ENDPOINT"))


class IsAuthenticated(APIView):
    """
    Returns whether a user is authenticated with Spotify or not.
    """

    def get(self, request, format=None):
        """
        Returns whether a user is authenticated with Spotify or not.
        """
        is_authenticated = is_spotify_authenticated(self.request.session.session_key)
        return Response({"status": is_authenticated}, status=status.HTTP_200_OK)


class CurrentSong(APIView):
    """
    Returns the current song playing for the host of the room the user is in.
    """

    def get(self, request, format=None):
        # Get the room code for the room the user is currently in
        room_code = self.request.session.get("room_code")

        # Retrieve the room from the database if it exists
        room = Room.objects.filter(code=room_code)
        if room.exists():
            room = room[0]
        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        # Identify the host of the room
        host = room.host

        # Make a GET request to Spotify to get the currently playing song for the Host
        endpoint = "player/currently-playing"
        response = execute_spotify_api_request(host, endpoint)

        # Handle the case where there is no song currently playing for the host
        if response.status_code == status.HTTP_200_OK:
            # Extract the relevant fields from the response
            response = response.json()
            item = response.get("item")
            duration = item.get("duration_ms")
            progress = response.get("progress_ms")
            album_cover = item.get("album").get("images")[0].get("url")
            is_playing = response.get("is_playing")
            song_id = item.get("id")

            # Parse the artists returned into pretty string format
            artist_string = ""
            for i, artist in enumerate(item.get("artists")):
                if i > 0:
                    artist_string += ", "
                name = artist.get("name")
                artist_string += name

            # Get the number of votes for the song
            votes = len(Vote.objects.filter(room=room, song_id=song_id))

            # Create a Song JSON object
            song = {
                "title": item.get("name"),
                "artist": artist_string,
                "duration": duration,
                "time": progress,
                "image_url": album_cover,
                "is_playing": is_playing,
                "votes": votes,
                "votes_required": room.votes_to_skip,
                "id": song_id,
            }

            # Update the room with the current song
            self.update_room_song(room, song_id)

            return Response(song, status=status.HTTP_200_OK)

        # Handle the case where there is no song currently playing for the host
        if response.status_code == status.HTTP_204_NO_CONTENT:
            return Response(
                {"Message": "No currently playing song for the host."},
                status=status.HTTP_204_NO_CONTENT,
            )

        # DEBUG
        print(response.text)

        return Response(
            {"Error": "Internal Server Error."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def update_room_song(self, room, song_id):
        """
        Updates the song for a Room and clears the votes if it is a different
        song that was previously in the database.
        """
        # Get the current song for the room
        current_song = room.current_song

        # Check if the current song is different that the stored song
        if current_song != song_id:
            # Update the current song for the Room in the database
            room.current_song = song_id
            room.save(update_fields=["current_song"])
            # Clear all the votes for the Room
            votes = Vote.objects.filter(room=room)
            votes.delete()


class PauseSong(APIView):
    """
    Pauses a song for a Room.
    """

    def put(self, response, format=None):
        """
        Pauses a song for a Room.
        """
        # Extract room code from the session
        room_code = self.request.session.get("room_code")
        # Get the Room from the database
        room = Room.objects.filter(code=room_code)[0]

        # Validate current user is host or the room allows guests to pause
        # and if so play the song
        if self.request.session.session_key == room.host or room.guest_can_pause:
            pause_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        # Return 403 to indication not allowed
        return Response({}, status=status.HTTP_403_FORBIDDEN)


class PlaySong(APIView):
    """
    Plays a song for a Room.
    """

    def put(self, response, format=None):
        """
        Plays a song for a Room.
        """
        # Extract room code from the session
        room_code = self.request.session.get("room_code")
        # Get the Room from the database
        room = Room.objects.filter(code=room_code)[0]

        # Validate current user is host or the room allows guests to pause
        # and if so play the song
        if self.request.session.session_key == room.host or room.guest_can_pause:
            play_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        # Return 403 to indication not allowed
        return Response({}, status=status.HTTP_403_FORBIDDEN)


class SkipSong(APIView):
    """
    Skip a song for a Room.
    """

    def put(self, request, format=None):
        """
        Skip a song for a Room.
        """
        # Extract the room code from the session
        room_code = self.request.session.get("room_code")
        # Get the Room from the database
        room = Room.objects.filter(code=room_code)[0]
        # Get votes for the Room from the database
        votes = Vote.objects.filter(room=room, song_id=room.current_song)
        # Get the number of votes needed to skip a song in this room
        votes_needed = room.votes_to_skip

        # Check if this user has already voted to skip this song
        if Vote.objects.filter(
            user=self.request.session.session_key, room=room, song_id=room.current_song
        ).exists():
            return Response(
                {"Message": "This user has already voted to skip this song"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Vaidate the current user is the host or with this additional vote do we have enough
        # votes to skip the song and if so skip the song
        if (
            self.request.session.session_key == room.host
            or len(votes) + 1 >= votes_needed
        ):
            # First delete all the votes related to the current song
            votes.delete()
            # Skip the song
            skip_song(room.host)
        # else create a new vote in the database
        else:
            vote = Vote(
                user=self.request.session.session_key,
                room=room,
                song_id=room.current_song,
            )
            vote.save()

        return Response({}, status=status.HTTP_204_NO_CONTENT)
