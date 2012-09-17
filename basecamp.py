#!/usr/bin/env python3
"""
basecamp.py is a simple Python interface to the basecamp API
defined here: https://github.com/37signals/bcx-api/

FIXME: More error checking is potentially required. Currently
any HTTPS errors will bubble up to the caller.
"""

import argparse
import base64
import http.client
import json
import os
import ssl

BASECAMP_HOST = 'basecamp.com'
USERAGENT = 'pybasecamp (benno@apkudo.com)'


class BasecampObject(object):
    def __init__(self, basecamp, raw):
        self.basecamp = basecamp
        self.raw = raw

    def __repr__(self):
        return '<%s id=%s name="%s">' % (self.__class__.__name__, self.raw['id'], self.raw['name'])


class Todo(BasecampObject):
    def __repr__(self):
        return '<%s id=%s position=%s>' % (self.__class__.__name__, self.raw['id'], self.raw['position'])


class Todolist(BasecampObject):
    def __init__(self, project, raw):
        super(Todolist, self).__init__(project.basecamp, raw)
        self.project = project

    def remaining(self):
        """Return all the todolist's todos"""
        full_info = self.basecamp._do_request('projects/%s/todolists/%s.json' %
                                              (self.project.raw['id'], self.raw['id']))
        return [Todo(self.basecamp, t) for t in full_info['todos']['remaining']]


class Project(BasecampObject):
    def todolists(self):
        """Return all the project's todo-lists"""
        return [Todolist(self, t) for t in
                self.basecamp._do_request('projects/%s/todolists.json' % self.raw['id'])]


class Basecamp(object):
    def __init__(self, account, username, password):
        self.account = account
        self.username = username
        self.password = password

        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self.ssl_context.set_default_verify_paths()
        self.connection = None

    def _do_request(self, url):
        raw = "%s:%s" % (self.username, self.password)
        auth = "Basic " + base64.b64encode(raw.encode()).decode("ascii")
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': USERAGENT,
            'Authorization': auth,
        }

        if self.connection is None:
            self.connection = http.client.HTTPSConnection(BASECAMP_HOST, context=self.ssl_context)

        url = '/%s/api/v1/%s' % (self.account, url)
        self.connection.request('GET', url, headers=headers)

        r = self.connection.getresponse()
        if r.status != 200:
            raise Exception('Unexpected return code: %s' % r.status)

        data = r.read()
        return json.loads(data.decode('utf-8'))

    def projects(self):
        """Return a list of projects."""
        return [Project(self, p) for p in self._do_request('projects.json')]


def main(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument('--user', default=os.environ.get('USER'),
                        help='user name')
    parser.add_argument('--password', help='password')
    parser.add_argument('--account', help='account')

    args = parser.parse_args(argv)

    bc = Basecamp(args.account, args.user, args.password)

    for p in bc.projects():
        print("%-8s: %s" % (p.raw['id'], p.raw['name']))
        for tl in p.todolists():
            print("          %s" % tl)
            for t in tl.remaining():
                print("            %-8s: %s" % (t.raw['id'], t.raw['content']))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
