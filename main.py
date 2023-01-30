# -*- coding: utf-8 -*-
import requests
import yaml
import time
import json
from account import Account


class App:
    def __init__(self):
        self.config_file = None
        self.config = {
            'graph_url': 'https://graph.microsoft.com/v1.0'
        }
        self.load_config()

    def load_config(self):
        with open('config.yaml', 'r') as f:
            self.config_file = yaml.safe_load(f)
            self.config['client_id'] = self.config_file['client_id']
            self.config['client_secret'] = self.config_file['client_secret']
            try:
                self.config['access_token'] = self.config_file['access_token']
                self.config['refresh_token'] = self.config_file['refresh_token']
                self.config['expires_at'] = self.config_file['expires_at']
            except KeyError:
                Account().get_access_token()
                self.load_config()

    def check_token(self):
        if self.config['expires_at'] < int(time.time()) - 60:
            Account().refresh_access_token(self.config['refresh_token'])
            self.load_config()

    def generate_header(self):
        return {'Authorization': f'Bearer {self.config["access_token"]}'}

    def get_drive(self):
        self.check_token()
        r = requests.get(f'{self.config["graph_url"]}/me/drive/root/children', headers=self.generate_header())
        print(r.json())
        with open('.response/me-drive-root-children.json', 'w') as f:
            json.dump(r.json(), f, indent=4)

    def process_data(self, r, method):
        print(r.json())
        values = r.json()['value']
        result = []
        if method == 'get_items':
            for value in values:
                result.append({
                    'id': value['id'],
                    'name': value['name'],
                    'is_folder': 'folder' in value
                })
        elif method == 'list_versions':
            for value in values:
                result.append(float(value['id']))
        return result

    def get_items_by_path(self, path: str) -> list:
        self.check_token()
        if path == '/':
            r = requests.get(f'{self.config["graph_url"]}/me/drive/root/children', headers=self.generate_header())
        else:
            r = requests.get(f'{self.config["graph_url"]}/me/drive/root:/{path}:/children', headers=self.generate_header())
        return self.process_data(r, 'get_items')

    def get_items_by_id(self, item_id: str) -> list:
        self.check_token()
        r = requests.get(f'{self.config["graph_url"]}/me/drive/items/{item_id}/children', headers=self.generate_header())
        return self.process_data(r, 'get_items')

    def list_versions(self, item_id: str) -> list:
        self.check_token()
        r = requests.get(f'{self.config["graph_url"]}/me/drive/items/{item_id}/versions', headers=self.generate_header())
        return self.process_data(r, 'list_versions')

    def delete_old_versions(self, item_id: str, versions: list = None, keep: int = 1):
        if versions is None:
            versions = self.list_versions(item_id)
        self.check_token()
        versions.sort(reverse=True)
        for version in versions[keep:]:
            r = requests.delete(f'{self.config["graph_url"]}/me/drive/items/{item_id}/versions/{version}',
                                headers=self.generate_header())
            print(r.status_code)


if __name__ == '__main__':
    a = App()
    print(a.delete_old_versions(''))
