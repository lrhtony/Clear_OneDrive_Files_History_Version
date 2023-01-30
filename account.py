# -*- coding: utf-8 -*-
import requests
import yaml
import webbrowser
import time
import urllib.parse
from threading import Thread
from wsgiref.simple_server import make_server, WSGIRequestHandler


class Account:
    def __init__(self):
        self.auth_code = None
        self.httpd = None
        with open('config.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
            self.client_id = self.config['client_id']
            self.client_secret = self.config['client_secret']
            try:
                self.access_token = self.config['access_token']
                self.refresh_token = self.config['refresh_token']
            except KeyError:
                self.access_token = None
                self.refresh_token = None

    def web_callback(self, environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
        self.auth_code = urllib.parse.parse_qs(environ['QUERY_STRING'])['code'][0]
        Thread(target=self.get_access_token_callback).start()
        return [b'Login Success! Please close the window and return to the terminal.']

    def get_access_token(self):
        scope = 'offline_access%20files.read%20files.read.all%20files.readwrite%20files.readwrite.all'
        redirect_uri = 'http%3A%2F%2Flocalhost%3A5000%2Fcallback'
        auth_url = f'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={self.client_id}&scope={scope}&response_type=code&redirect_uri={redirect_uri}'
        webbrowser.open(auth_url)

        class NoLoggingWSGIRequestHandler(WSGIRequestHandler):  # https://stackoverflow.com/a/31904641/18966310
            def log_message(self, format, *args):
                pass
        self.httpd = make_server('', 5000, self.web_callback, handler_class=NoLoggingWSGIRequestHandler)  # Create the server
        self.httpd.serve_forever()  # Start the server
        print(f'auth_code: {self.auth_code}')
        data = {
            'client_id': self.client_id,
            'redirect_uri': 'http://localhost:5000/callback',
            'client_secret': self.client_secret,
            'code': self.auth_code,
            'grant_type': 'authorization_code'
        }
        r = requests.post('https://login.microsoftonline.com/common/oauth2/v2.0/token', data=data)
        print(r.json())
        self.config['access_token'] = r.json()['access_token']
        self.config['refresh_token'] = r.json()['refresh_token']
        self.config['expires_at'] = int(time.time()) + r.json()['expires_in']
        with open('config.yaml', 'w') as f:
            yaml.safe_dump(self.config, f)

    def get_access_token_callback(self):
        self.httpd.shutdown()  # Stop the server

    def refresh_access_token(self, refresh_token):
        data = {
            'client_id': self.client_id,
            'redirect_uri': 'http://localhost:5000/callback',
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        r = requests.post('https://login.microsoftonline.com/common/oauth2/v2.0/token', data=data)
        print(r.json())
        self.config['access_token'] = r.json()['access_token']
        self.config['refresh_token'] = r.json()['refresh_token']
        self.config['expires_at'] = int(time.time()) + r.json()['expires_in']
        with open('config.yaml', 'w') as f:
            yaml.safe_dump(self.config, f)


if __name__ == '__main__':
    a = Account()
    # a.get_access_token()
    a.refresh_access_token(a.refresh_token)
