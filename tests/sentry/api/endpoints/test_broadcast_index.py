from __future__ import absolute_import

from django.core.urlresolvers import reverse

from sentry.models import Broadcast
from sentry.testutils import APITestCase


class BroadcastIndexTest(APITestCase):
    def test_simple(self):
        broadcast1 = Broadcast.objects.create(message='bar', is_active=True)
        broadcast2 = Broadcast.objects.create(message='foo', is_active=False)

        self.login_as(user=self.user)
        url = reverse('sentry-api-0-broadcast-index')
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['id'] == str(broadcast1.id)