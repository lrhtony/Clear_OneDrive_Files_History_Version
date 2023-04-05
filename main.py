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
        self.s = requests.Session()
        self.result = []

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

    def process_data(self, r, method):
        with open('.response/response.json', 'w') as f:
            json.dump(r.json(), f, indent=2)
        values = r.json()['value']
        if method != 'get_items_next':
            self.result = []
        if method == 'get_items' or method == 'get_items_next':
            for value in values:
                self.result.append({
                    'id': value['id'],
                    'name': value['name'],
                    'path': value['parentReference']['path'].replace('/drive/root:', '').replace(':', '/'),
                    'is_folder': 'folder' in value
                })
            if '@odata.nextLink' in r.json():
                self.get_items_next(r.json()['@odata.nextLink'])
        elif method == 'list_versions':
            for value in values:
                self.result.append(float(value['id']))
        return self.result

    def get_items_by_path(self, path: str) -> list:
        self.check_token()
        if path == '/':
            r = self.s.get(f'{self.config["graph_url"]}/me/drive/root/children', headers=self.generate_header(), timeout=10)
        else:
            r = self.s.get(f'{self.config["graph_url"]}/me/drive/root:/{path}:/children', headers=self.generate_header(), timeout=10)
        return self.process_data(r, 'get_items')

    def get_items_by_id(self, item_id: str) -> list:
        self.check_token()
        r = self.s.get(f'{self.config["graph_url"]}/me/drive/items/{item_id}/children', headers=self.generate_header(), timeout=10)
        return self.process_data(r, 'get_items')

    def get_items_next(self, url: str):
        self.check_token()
        r = self.s.get(url, headers=self.generate_header())
        self.process_data(r, 'get_items_next')

    def list_versions(self, item_id: str) -> list:
        self.check_token()
        r = self.s.get(f'{self.config["graph_url"]}/me/drive/items/{item_id}/versions', headers=self.generate_header(), timeout=10)
        return self.process_data(r, 'list_versions')

    def delete_old_versions(self, item_id: str, versions: list = None, keep: int = 1):
        if versions is None:
            versions = self.list_versions(item_id)
        self.check_token()
        versions.sort(reverse=True)
        for version in versions[keep:]:
            r = self.s.delete(f'{self.config["graph_url"]}/me/drive/items/{item_id}/versions/{version}', headers=self.generate_header(), timeout=10)
            print(r.status_code)

    def delete_folder_old_versions(self, keep: int = 1, **kwargs):
        if 'id' in kwargs:
            items = self.get_items_by_id(kwargs['id'])
        elif 'path' in kwargs:
            items = self.get_items_by_path(kwargs['path'])
        else:
            raise KeyError('id or path is required')
        for item in items:
            if item['is_folder']:
                print(f'Processing folder: {item["path"]}/{item["name"]}')
                self.delete_folder_old_versions(id=item['id'], keep=keep)
            else:
                print(f'Processing file: {item["path"]}/{item["name"]}')
                self.delete_old_versions(item['id'], keep=keep)

    def get_download_url_by_path(self, path: str):
        self.check_token()
        r = self.s.get(f'{self.config["graph_url"]}/me/drive/root:/{path}?select=id,@microsoft.graph.downloadUrl', headers=self.generate_header(), allow_redirects=False, timeout=10)
        if r.status_code == 200:
            return r.json()


if __name__ == '__main__':
    a = App()
    a.delete_folder_old_versions(path='/music')
