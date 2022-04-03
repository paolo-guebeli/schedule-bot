import datetime
import json
import os
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from icalendar import Calendar, Event
from file_manager import FileManager


class CalendarManager:

    def __init__(self, path):
        self.path = path
        self.updates = {}

    def download_wait(self):
        seconds = 0
        dl_wait = True
        while dl_wait and seconds < 20:
            time.sleep(1)
            dl_wait = False
            for fname in os.listdir(self.path):
                if fname.endswith('.crdownload'):
                    dl_wait = True
            seconds += 1

    def get_calendar(self, guild):
        guild = guild.replace(' ', '_').lower()
        dir = os.path.join(os.getcwd(), self.path)
        accounts = FileManager.get_accounts()
        account = accounts[guild]
        options = Options()
        options.headless = True
        options.add_experimental_option("prefs", {
            "download.default_directory": dir})
        try:
            driver = webdriver.Chrome(options=options)

            driver.get("http://www.icorsi.ch")
            driver.find_element(By.LINK_TEXT, "Login SUPSI").click()
            username = driver.find_element(By.ID, "username")
            pwd = driver.find_element(By.ID, "password")
            username.clear()
            pwd.clear()
            username.send_keys(account['email'])
            pwd.send_keys(account['password'])

            driver.find_element(By.NAME, "_eventId_proceed").click()

            driver.get("https://www.icorsi.ch/calendar/export.php?")

            driver.find_element(By.ID, "id_events_exportevents_all").click()
            driver.find_element(By.ID, "id_period_timeperiod_recentupcoming").click()
            driver.find_element(By.ID, "id_export").click()

            self.download_wait()
            driver.quit()
            self.homework_to_json(guild)
        except WebDriverException:
            print("There's a problem with the chrome intallation.")

    def homework_to_json(self, guild):
        guild = guild.replace(' ', '_').lower()
        events = []
        modules = FileManager.get_modules()

        with open(f'{self.path}/icalexport.ics') as file:
            calendar = Calendar.from_ical(file.read())
            for component in calendar.walk():
                if component.name == "VEVENT":
                    mod = component.get('categories').to_ical().decode("UTF-8")
                    channel = None
                    if 'DTI' in mod:
                        mod = mod[4:]
                    if mod in list(modules.keys()):
                        channel = modules[mod]

                    events.append(
                        {
                            'channel': channel,
                            'title': str(component.get('summary')),
                            'end_time': (component.get('dtend').dt.replace(tzinfo=None) + datetime.timedelta(
                                hours=2)).strftime('%y-%m-%d %H:%M:%S')
                        }
                    )
        os.remove(f'{self.path}/icalexport.ics')
        with open(f'{self.path}/{guild}_calendar.json', 'w') as file:
            json.dump(events, file)
        self.updates[guild] = datetime.datetime.now()

    def get_homework(self, guild, channel):
        guild = guild.replace(' ', '_').lower()
        now = datetime.datetime.now()
        path = os.path.join(os.getcwd(), self.path, f'{guild}_calendar.json')
        homework = []
        if os.path.exists(path):
            with open(f'{self.path}/{guild}_calendar.json') as file:
                hws = list(json.loads(file.read()))
            for hw in hws:
                hw['end_time'] = datetime.datetime.strptime(hw['end_time'], '%y-%m-%d %H:%M:%S')
                print(hw)
                if channel:
                    if hw['channel'] == channel:
                        if now <= hw['end_time']:
                            homework.append(hw)
                else:
                    if now <= hw['end_time']:
                        homework.append(hw)
        return homework
