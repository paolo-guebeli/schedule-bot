import datetime
import json
import os


class FileManager:

    @staticmethod
    def get_channels(guild):
        guild = guild.replace(' ', '_')
        channels = {}
        path = os.path.join(os.getcwd(), 'management', f'{guild.lower()}_channels.json')
        if os.path.exists(path):
            with open(path, 'r') as file:
                channels = json.load(file)
        return channels

    @staticmethod
    def get_schedule(guild):
        guild = guild.replace(' ', '_')
        path = os.path.join(os.getcwd(), 'management', f' {guild.lower()}.json')
        data = []
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = list(json.loads(file.read()))
            for day in data:
                for lecture in day:
                    lecture['start_time'] = datetime.datetime.strptime(
                        lecture['start_time'], '%H:%M:%S').time()
                    lecture['end_time'] = datetime.datetime.strptime(
                        lecture['end_time'], '%H:%M:%S').time()
        if len(data) < 7:
            for _ in range(7 - len(data)):
                data.append([])
        return data

    @staticmethod
    def get_modules():
        modules = []
        path = os.path.join(os.getcwd(), 'management', f'modules.json')
        if os.path.exists(path):
            with open(path, 'r') as file:
                modules = dict(json.loads(file.read()))
        return modules

    @staticmethod
    def get_accounts():
        accounts = []
        path = os.path.join(os.getcwd(), 'management', f'accounts.json')
        if os.path.exists(path):
            with open(path, 'r') as file:
                accounts = dict(json.loads(file.read()))
        return accounts
