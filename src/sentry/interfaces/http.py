"""
sentry.interfaces.http
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2014 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""

__all__ = ('Http',)

from django.utils.translation import ugettext as _
from urllib import urlencode
from urlparse import parse_qsl, urlsplit, urlunsplit

from sentry.constants import HTTP_METHODS
from sentry.interfaces.base import Interface
from sentry.utils.safe import trim, trim_dict
from sentry.web.helpers import render_to_string


class Http(Interface):
    """
    The Request information is stored in the Http interface. Two arguments
    are required: ``url`` and ``method``.

    The ``env`` variable is a compounded dictionary of HTTP headers as well
    as environment information passed from the webserver. Sentry will explicitly
    look for ``REMOTE_ADDR`` in ``env`` for things which require an IP address.

    The ``data`` variable should only contain the request body (not the query
    string). It can either be a dictionary (for standard HTTP requests) or a
    raw request body.

    >>>  {
    >>>     "url": "http://absolute.uri/foo",
    >>>     "method": "POST",
    >>>     "data": {
    >>>         "foo": "bar"
    >>>     },
    >>>     "query_string": "hello=world",
    >>>     "cookies": "foo=bar",
    >>>     "headers": {
    >>>         "Content-Type": "text/html"
    >>>     },
    >>>     "env": {
    >>>         "REMOTE_ADDR": "192.168.0.1"
    >>>     }
    >>>  }

    .. note:: This interface can be passed as the 'request' key in addition
              to the full interface path.
    """
    display_score = 1000
    score = 800

    FORM_TYPE = 'application/x-www-form-urlencoded'

    @classmethod
    def to_python(cls, data):
        assert data.get('url')

        kwargs = {}

        if data.get('method'):
            method = data['method'].upper()
            assert method in HTTP_METHODS
            kwargs['method'] = method
        else:
            kwargs['method'] = None

        scheme, netloc, path, query_bit, fragment_bit = urlsplit(data['url'])

        query_string = data.get('query_string') or query_bit
        if query_string:
            # if querystring was a dict, convert it to a string
            if isinstance(query_string, dict):
                query_string = urlencode(query_string.items())
            else:
                query_string = query_string
                if query_string[0] == '?':
                    # remove '?' prefix
                    query_string = query_string[1:]
            kwargs['query_string'] = trim(query_string, 1024)
        else:
            kwargs['query_string'] = ''

        fragment = data.get('fragment') or fragment_bit

        cookies = data.get('cookies')
        # if cookies were [also] included in headers we
        # strip them out
        headers = data.get('headers')
        if headers:
            if 'Cookie' in headers and not cookies:
                cookies = headers.pop('Cookie')
            headers = trim_dict(headers)
        else:
            headers = {}

        body = data.get('data')
        if isinstance(body, (list, tuple)):
            body = trim_dict(dict(enumerate(body)))
        elif isinstance(body, dict):
            body = trim_dict(body)
        elif body:
            body = trim(body, 2048)
            if headers.get('Content-Type') == cls.FORM_TYPE and '=' in body:
                body = dict(parse_qsl(body))

        # if cookies were a string, convert to a dict
        # parse_qsl will parse both acceptable formats:
        #  a=b&c=d
        # and
        #  a=b;c=d
        if isinstance(cookies, basestring):
            cookies = dict(parse_qsl(cookies, keep_blank_values=True))
        elif not cookies:
            cookies = {}

        kwargs['cookies'] = trim_dict(cookies)
        kwargs['env'] = trim_dict(data.get('env') or {})
        kwargs['headers'] = headers
        kwargs['data'] = body
        kwargs['url'] = urlunsplit((scheme, netloc, path, '', ''))
        kwargs['fragment'] = trim(fragment, 256)

        return cls(**kwargs)

    def get_path(self):
        return 'sentry.interfaces.Http'

    @property
    def full_url(self):
        url = self.url
        if self.query_string:
            url = url + '?' + self.query_string
        if self.fragment:
            url = url + '#' + self.fragment
        return url

    def to_email_html(self, event, **kwargs):
        return render_to_string('sentry/partial/interfaces/http_email.html', {
            'event': event,
            'url': self.full_url,
            'short_url': self.url,
            'method': self.method,
            'query_string': self.query_string,
        })

    def to_html(self, event, is_public=False, **kwargs):
        context = {
            'is_public': is_public,
            'event': event,
            'url': self.full_url,
            'short_url': self.url,
            'method': self.method,
            'query_string': self.query_string,
            'fragment': self.fragment,
            'headers': self.headers,
        }
        if not is_public:
            # It's kind of silly we store this twice
            context.update({
                'cookies': self.cookies,
                'env': self.env,
                'data': self.data,
            })

        return render_to_string('sentry/partial/interfaces/http.html', context)

    def get_alias(self):
        return 'request'

    def get_title(self):
        return _('Request')
