"""
Model and view tests for the music app.

Covers Song model properties, Playlist CRUD views, and song add/remove.
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from music.models import Playlist, Song


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username, password="testpass123"):
    return User.objects.create_user(username=username, password=password)


def make_song(name="Song", artist="Artist", spotify_id=None, tags=None, popularity=70):
    return Song.objects.create(
        name=name,
        artist=artist,
        album="Album",
        year="2020",
        genre="Pop",
        photo="http://example.com/photo.jpg",
        spotify_id=spotify_id or f"sp_{name.replace(' ', '_')}",
        popularity=popularity,
        lastfm_tags=tags or {},
    )


# ---------------------------------------------------------------------------
# Song model tests
# ---------------------------------------------------------------------------

class TestSongModel(TestCase):

    def test_str_representation(self):
        song = make_song("Bohemian Rhapsody", "Queen", "sp_bq")
        self.assertEqual(str(song), "Bohemian Rhapsody - Queen")

    def test_top_tags_returns_sorted_list(self):
        song = make_song(tags={"rock": 0.9, "classic rock": 0.7, "pop": 0.3})
        tags = song.top_tags
        self.assertEqual(tags[0][0], "rock")
        self.assertEqual(tags[0][1], 0.9)

    def test_top_tags_returns_at_most_five(self):
        many_tags = {f"tag{i}": 1.0 - i * 0.1 for i in range(10)}
        song = make_song(tags=many_tags)
        self.assertLessEqual(len(song.top_tags), 5)

    def test_top_tags_empty_when_no_tags(self):
        song = make_song(tags={})
        self.assertEqual(song.top_tags, [])

    def test_primary_tag_returns_highest_weight_tag(self):
        song = make_song(tags={"rock": 0.9, "pop": 0.5})
        self.assertEqual(song.primary_tag, "rock")

    def test_primary_tag_returns_none_when_no_tags(self):
        song = make_song(tags={})
        self.assertIsNone(song.primary_tag)


# ---------------------------------------------------------------------------
# Playlist model tests
# ---------------------------------------------------------------------------

class TestPlaylistModel(TestCase):

    def test_str_representation(self):
        user = make_user("playlist_str_user")
        playlist = Playlist.objects.create(name="My Playlist", user=user)
        self.assertIn("My Playlist", str(playlist))
        self.assertIn("playlist_str_user", str(playlist))

    def test_playlist_default_is_not_public(self):
        user = make_user("private_default_user")
        playlist = Playlist.objects.create(name="Private by Default", user=user)
        self.assertFalse(playlist.is_public)

    def test_playlist_ordered_by_created_at_descending(self):
        user = make_user("order_user")
        p1 = Playlist.objects.create(name="First", user=user)
        p2 = Playlist.objects.create(name="Second", user=user)
        playlists = list(Playlist.objects.filter(user=user))
        self.assertEqual(playlists[0], p2)
        self.assertEqual(playlists[1], p1)


# ---------------------------------------------------------------------------
# Playlist views integration tests
# ---------------------------------------------------------------------------

class TestPlaylistViews(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user("view_user")
        self.other = make_user("other_view_user")
        self.client.login(username="view_user", password="testpass123")

    def test_playlists_view_returns_200(self):
        response = self.client.get(reverse('music:playlists'))
        self.assertEqual(response.status_code, 200)

    def test_create_playlist_get_returns_200(self):
        response = self.client.get(reverse('music:create_playlist'))
        self.assertEqual(response.status_code, 200)

    def test_playlist_detail_returns_200_for_public(self):
        playlist = Playlist.objects.create(name="Public", user=self.other, is_public=True)
        response = self.client.get(reverse('music:playlist_detail', args=[playlist.id]))
        self.assertEqual(response.status_code, 200)

    def test_playlist_detail_redirects_for_private_non_owner(self):
        playlist = Playlist.objects.create(name="Private", user=self.other, is_public=False)
        response = self.client.get(reverse('music:playlist_detail', args=[playlist.id]))
        # View redirects to playlists list when access is denied
        self.assertEqual(response.status_code, 302)

    def test_playlist_detail_owner_can_view_private(self):
        self.client.login(username="other_view_user", password="testpass123")
        playlist = Playlist.objects.create(name="My Private", user=self.other, is_public=False)
        response = self.client.get(reverse('music:playlist_detail', args=[playlist.id]))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_redirected_from_playlists(self):
        self.client.logout()
        response = self.client.get(reverse('music:playlists'))
        self.assertIn(response.status_code, [302, 403])
