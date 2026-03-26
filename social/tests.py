"""
Integration tests for social features.

Covers follow/unfollow, messaging, comments, notifications, and the feed view.
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from music.models import Playlist, Song
from social.models import (
    Activity,
    Conversation,
    Message,
    Notification,
    PlaylistComment,
    PlaylistFollow,
    UserFollow,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username, password="testpass123"):
    return User.objects.create_user(username=username, password=password)


def make_song(name="Song", artist="Artist", spotify_id=None):
    return Song.objects.create(
        name=name,
        artist=artist,
        album="Album",
        year="2020",
        genre="Pop",
        photo="http://example.com/photo.jpg",
        spotify_id=spotify_id or f"sp_{name.replace(' ', '')}",
    )


def make_playlist(name, user, public=True):
    return Playlist.objects.create(name=name, user=user, is_public=public)


# ---------------------------------------------------------------------------
# follow_user tests
# ---------------------------------------------------------------------------

class TestFollowUser(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user("follower_user")
        self.target = make_user("target_user")
        self.client.login(username="follower_user", password="testpass123")

    def test_follow_creates_userfollow_record(self):
        self.client.post(
            reverse('social:follow_user', args=[self.target.username]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertTrue(
            UserFollow.objects.filter(follower=self.user, following=self.target).exists()
        )

    def test_follow_returns_following_true(self):
        response = self.client.post(
            reverse('social:follow_user', args=[self.target.username]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = json.loads(response.content)
        self.assertTrue(data['following'])

    def test_follow_creates_notification_for_target(self):
        self.client.post(
            reverse('social:follow_user', args=[self.target.username]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.target,
                sender=self.user,
                notification_type='follow',
            ).exists()
        )

    def test_follow_creates_activity(self):
        self.client.post(
            reverse('social:follow_user', args=[self.target.username]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertTrue(
            Activity.objects.filter(
                user=self.user,
                activity_type='user_followed',
                target_user=self.target,
            ).exists()
        )

    def test_unfollow_deletes_userfollow_record(self):
        UserFollow.objects.create(follower=self.user, following=self.target)

        self.client.post(
            reverse('social:follow_user', args=[self.target.username]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertFalse(
            UserFollow.objects.filter(follower=self.user, following=self.target).exists()
        )

    def test_unfollow_returns_following_false(self):
        UserFollow.objects.create(follower=self.user, following=self.target)

        response = self.client.post(
            reverse('social:follow_user', args=[self.target.username]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = json.loads(response.content)
        self.assertFalse(data['following'])

    def test_follow_self_returns_400(self):
        response = self.client.post(
            reverse('social:follow_user', args=[self.user.username]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_follow_redirects(self):
        self.client.logout()
        response = self.client.post(
            reverse('social:follow_user', args=[self.target.username]),
        )
        self.assertIn(response.status_code, [302, 403])


# ---------------------------------------------------------------------------
# follow_playlist tests
# ---------------------------------------------------------------------------

class TestFollowPlaylist(TestCase):

    def setUp(self):
        self.client = Client()
        self.owner = make_user("playlist_owner")
        self.follower = make_user("playlist_follower")
        self.playlist = make_playlist("Public Playlist", self.owner, public=True)
        self.client.login(username="playlist_follower", password="testpass123")

    def test_follow_playlist_creates_record(self):
        self.client.post(reverse('social:follow_playlist', args=[self.playlist.id]))
        self.assertTrue(
            PlaylistFollow.objects.filter(user=self.follower, playlist=self.playlist).exists()
        )

    def test_follow_playlist_creates_notification(self):
        self.client.post(reverse('social:follow_playlist', args=[self.playlist.id]))
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner,
                sender=self.follower,
                notification_type='playlist_follow',
            ).exists()
        )

    def test_follow_playlist_creates_activity(self):
        self.client.post(reverse('social:follow_playlist', args=[self.playlist.id]))
        self.assertTrue(
            Activity.objects.filter(
                user=self.follower,
                activity_type='playlist_followed',
                playlist=self.playlist,
            ).exists()
        )

    def test_unfollow_playlist_deletes_record(self):
        PlaylistFollow.objects.create(user=self.follower, playlist=self.playlist)
        self.client.post(reverse('social:follow_playlist', args=[self.playlist.id]))
        self.assertFalse(
            PlaylistFollow.objects.filter(user=self.follower, playlist=self.playlist).exists()
        )

    def test_follow_private_playlist_returns_403(self):
        private = make_playlist("Private", self.owner, public=False)
        response = self.client.post(reverse('social:follow_playlist', args=[private.id]))
        self.assertEqual(response.status_code, 403)

    def test_follow_own_playlist_does_not_create_notification(self):
        self.client.login(username="playlist_owner", password="testpass123")
        self.client.post(reverse('social:follow_playlist', args=[self.playlist.id]))
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.owner,
                notification_type='playlist_follow',
            ).exists()
        )

    def test_follow_returns_followers_count(self):
        response = self.client.post(reverse('social:follow_playlist', args=[self.playlist.id]))
        data = json.loads(response.content)
        self.assertIn('followers_count', data)


# ---------------------------------------------------------------------------
# send_message tests
# ---------------------------------------------------------------------------

class TestSendMessage(TestCase):

    def setUp(self):
        self.client = Client()
        self.sender = make_user("msg_sender")
        self.recipient = make_user("msg_recipient")
        self.client.login(username="msg_sender", password="testpass123")

    def _post_message(self, content, recipient_username=None, conversation_id=None):
        payload = {'content': content}
        if recipient_username:
            payload['recipient'] = recipient_username
        if conversation_id:
            payload['conversation_id'] = conversation_id
        return self.client.post(
            reverse('social:send_message'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_send_message_creates_conversation_and_message(self):
        response = self._post_message("Hello!", recipient_username="msg_recipient")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['message']['content'], "Hello!")

    def test_send_message_to_existing_conversation(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.sender, self.recipient)

        response = self._post_message("Reply!", conversation_id=conv.id)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(Message.objects.filter(conversation=conv).exists())

    def test_send_empty_message_returns_400(self):
        response = self._post_message("", recipient_username="msg_recipient")
        self.assertEqual(response.status_code, 400)

    def test_send_message_to_self_returns_400(self):
        response = self._post_message("Hi", recipient_username="msg_sender")
        self.assertEqual(response.status_code, 400)

    def test_send_message_malformed_json_returns_400(self):
        response = self.client.post(
            reverse('social:send_message'),
            data="not valid json",
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_send_message_no_conversation_or_recipient_returns_400(self):
        response = self._post_message("Hello!")
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# add_comment tests
# ---------------------------------------------------------------------------

class TestAddComment(TestCase):

    def setUp(self):
        self.client = Client()
        self.owner = make_user("comment_owner")
        self.commenter = make_user("commenter")
        self.playlist = make_playlist("Commented Playlist", self.owner, public=True)
        self.client.login(username="commenter", password="testpass123")

    def _post_comment(self, content, playlist_id=None, parent_id=None):
        payload = {'content': content}
        if parent_id:
            payload['parent_id'] = parent_id
        pid = playlist_id or self.playlist.id
        return self.client.post(
            reverse('social:add_comment', args=[pid]),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_add_comment_creates_record(self):
        self._post_comment("Great playlist!")
        self.assertTrue(
            PlaylistComment.objects.filter(
                playlist=self.playlist, user=self.commenter
            ).exists()
        )

    def test_add_comment_creates_notification(self):
        self._post_comment("Nice!")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner,
                sender=self.commenter,
                notification_type='comment',
            ).exists()
        )

    def test_add_comment_returns_comment_data(self):
        response = self._post_comment("Awesome!")
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['comment']['content'], "Awesome!")
        self.assertEqual(data['comment']['user'], "commenter")

    def test_add_empty_comment_returns_400(self):
        response = self._post_comment("")
        self.assertEqual(response.status_code, 400)

    def test_add_comment_to_private_playlist_returns_403(self):
        private = make_playlist("Private", self.owner, public=False)
        response = self._post_comment("Hi", playlist_id=private.id)
        self.assertEqual(response.status_code, 403)

    def test_add_comment_malformed_json_returns_400(self):
        response = self.client.post(
            reverse('social:add_comment', args=[self.playlist.id]),
            data="not json",
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_add_own_comment_does_not_create_notification(self):
        self.client.login(username="comment_owner", password="testpass123")
        self._post_comment("My own comment")
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.owner,
                notification_type='comment',
            ).exists()
        )


# ---------------------------------------------------------------------------
# social_feed tests
# ---------------------------------------------------------------------------

class TestSocialFeed(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user("feed_user")
        self.other = make_user("feed_other")
        self.client.login(username="feed_user", password="testpass123")

    def test_feed_returns_200(self):
        response = self.client.get(reverse('social:feed'))
        self.assertEqual(response.status_code, 200)

    def test_feed_contains_popular_users_context(self):
        response = self.client.get(reverse('social:feed'))
        self.assertIn('popular_users', response.context)

    def test_feed_contains_trending_playlists_context(self):
        response = self.client.get(reverse('social:feed'))
        self.assertIn('trending_playlists', response.context)

    def test_feed_shows_followed_user_activities(self):
        UserFollow.objects.create(follower=self.user, following=self.other)
        playlist = make_playlist("Other's Playlist", self.other, public=True)
        Activity.objects.create(
            user=self.other,
            activity_type='playlist_created',
            playlist=playlist,
        )

        response = self.client.get(reverse('social:feed'))
        self.assertIn(
            Activity.objects.get(user=self.other),
            response.context['activities'],
        )

    def test_unauthenticated_feed_redirects(self):
        self.client.logout()
        response = self.client.get(reverse('social:feed'))
        self.assertIn(response.status_code, [302, 403])


# ---------------------------------------------------------------------------
# Model method tests
# ---------------------------------------------------------------------------

class TestConversationModel(TestCase):

    def test_get_other_participant_returns_other_user(self):
        user1 = make_user("conv_user1")
        user2 = make_user("conv_user2")
        conv = Conversation.objects.create()
        conv.participants.add(user1, user2)

        other = conv.get_other_participant(user1)
        self.assertEqual(other, user2)

    def test_get_last_message_returns_most_recent(self):
        user1 = make_user("msg_u1")
        user2 = make_user("msg_u2")
        conv = Conversation.objects.create()
        conv.participants.add(user1, user2)

        msg1 = Message.objects.create(conversation=conv, sender=user1, content="First")
        msg2 = Message.objects.create(conversation=conv, sender=user2, content="Last")

        last = conv.get_last_message()
        self.assertEqual(last, msg2)
