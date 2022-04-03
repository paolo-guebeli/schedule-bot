import asyncio
import json
import os
import time
import settings

import discord
from discord.ext import commands
import datetime

import requests
from bs4 import BeautifulSoup

from calendar_manager import CalendarManager
from file_manager import FileManager

print('ok')

cm = CalendarManager('calendars')

TOKEN = settings.TOKEN

client = discord.Client()

bot = commands.Bot(command_prefix='$', case_insensitive=True)

stop = False

green_circle = '\U0001F7E2'
orange_circle = '\U0001F7E0'

tasks = {}

days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}


@bot.event
async def on_ready():
    start()


def start():
    files = os.listdir(os.path.join(os.getcwd(), 'schedules'))
    for file in files:
        guild = file.split('.')[0]
        cm.get_calendar(guild)
        tasks[guild] = asyncio.get_event_loop().create_task(schedule_manager(guild))


@bot.command()
async def stop(ctx):
    if ctx.guild in tasks:
        try:
            tasks[ctx.guild].cancel()
        except asyncio.CancelledError:
            await ctx.send(f'The scheduler has been stopped.')


async def schedule_manager(guild):
    schedule = FileManager.get_schedule(guild)
    channels = FileManager.get_channels(guild)
    active_lecture = None
    orange_lecture = None
    print('started')
    while True:
        print(f'check {guild}')
        now = datetime.datetime.now()
        nl = await next_lecture(guild)
        if nl:
            if nl['end_time'] > now.time():
                sleep_time = await seconds_diff(nl['start_time'], now.time())
            else:
                sleep_time = 3600
        else:
            sleep_time = 3600
        if active_lecture:
            sleep_time = await seconds_diff(active_lecture['end_time'], now.time())
            if active_lecture['end_time'] < now.time():
                channel = bot.get_channel(channels[active_lecture['id']])
                await channel.edit(name=active_lecture['og_name'])
                print(f"The {active_lecture['og_name']} has ended.")
                active_lecture = None
        for lecture in schedule[now.weekday()]:
            channel = None
            if lecture['start_time'] <= now.time() <= lecture['end_time'] and not active_lecture:
                print(lecture['id'])
                if lecture['id'] in channels:
                    channel = bot.get_channel(channels[lecture['id']])
                print(channel)
                if channel:
                    if orange_lecture and orange_lecture['id'] == lecture['id']:
                        if green_circle not in channel.name:
                            new_name = green_circle + '' + orange_lecture['og_name']
                            await channel.edit(name=new_name)
                            active_lecture = orange_lecture
                            orange_lecture = None
                    else:
                        print(f"active lecture: {lecture['id']}")
                        active_lecture = lecture
                        if green_circle not in channel.name:
                            active_lecture['og_name'] = channel.name
                            new_name = green_circle + '' + channel.name
                            await channel.edit(name=new_name)
                        else:
                            active_lecture = lecture
                            active_lecture['og_name'] = channel.name[1:]
                sleep_time = await seconds_diff(active_lecture['end_time'], now.time())
            if (now + datetime.timedelta(minutes=15)).time() >= lecture['start_time'] >= now.time():
                if not orange_lecture:
                    if lecture['id'] in channels:
                        channel = bot.get_channel(channels[lecture['id']])
                    if channel:
                        print(f"next lecture: {lecture['id']}")
                        orange_lecture = lecture
                        if orange_circle not in channel.name:
                            orange_lecture['og_name'] = channel.name
                            new_name = orange_circle + '' + channel.name
                            await channel.edit(name=new_name)
        if sleep_time < 60:
            sleep_time = 60
        if sleep_time > 3600:
            sleep_time = 3600
        print(sleep_time)
        await asyncio.sleep(sleep_time)


@bot.command()
async def now(ctx):
    print('now')
    schedule = FileManager.get_schedule(ctx.guild)
    now = datetime.datetime.now()
    for lecture in schedule[now.weekday()]:
        if lecture['start_time'] <= now.time() <= lecture['end_time']:
            await ctx.send(f"The current lecture is {lecture['id']}.")
            return
    await ctx.send(
        'No Lecture right now have fun! (you probably have to do some assignment)'
    )


@bot.command()
async def next(ctx):
    print('next')
    nl = await next_lecture(ctx.guild)
    if not nl:
        ctx.send('No lecture scheduled.')
    ctx.send(f"The next lecture is {nl['id']} at {nl['start_time']}")


async def next_lecture(guild):
    schedule = FileManager.get_schedule(guild)
    now = datetime.datetime.now()
    next_lecture = None
    for lecture in schedule[now.weekday()]:
        if lecture['start_time'] <= now.time():
            if lecture == schedule[now.weekday()][-1]:
                next_day = now.weekday()
                while True:
                    if next_day == 6:
                        next_day = 0
                    else:
                        next_day += 1
                    if len(schedule[next_day]) > 0:
                        next_lecture = schedule[next_day][0]
                        break
            else:
                lecture = schedule[now.weekday()][schedule[now.weekday()].index(lecture) + 1]
                if lecture['start_time'] <= now.time():
                    continue
                next_lecture = lecture
        else:
            return lecture
    return next_lecture


async def seconds_diff(a, b):
    return a.second - b.second + (a.minute - b.minute) * 60 + (a.hour - b.hour) * 3600


@bot.command()
async def menu(ctx, day: str = None, campus: str = None):
    print('menu')
    now = datetime.datetime.now()
    today = now.weekday()
    usi = False
    if campus and campus.lower() == 'usi':
        usi = True

    if today > 5:
        today = 5
    if day:
        if day.lower() in list(days.keys()):
            day = days[day.lower()]
            if day < 5:
                if today > day:
                    day = 5 - today + day
                elif today < day:
                    day = day - today
                else:
                    day = 0
            else:
                await ctx.send("Saturday and Sunday the canteen is closed.")
                return
        elif day.lower() == 'usi':
            usi = True
            day = 0
        elif day.lower() == 'supsi':
            usi = False
            day = 0
        else:
            await ctx.send("Invalid day. (come on it's simple english)")
            return
    menu = get_menu(day, usi)
    await ctx.send(menu)


def get_menu(day=None, usi=False):
    if not day:
        day = 0
    if 0 <= day < 5:
        if usi:
            URL = 'https://polo-universitario-lugano.sv-restaurant.ch/en/menu/campus-ovest/'
        else:
            URL = 'https://polo-universitario-lugano.sv-restaurant.ch/en/menu/campus-est/'
        page = requests.get(URL)

        text = ''
        soup = BeautifulSoup(page.content, "html.parser")
        menus = soup.find_all("div", class_='menu-plan-grid')
        items = menus[day].find_all("div", class_='menu-item')
        for item in items:
            title = item.find_all("span", class_='menuline')[0]
            desc = item.find_all("h2", class_='menu-title')[0]
            tab = 1
            if len(title.text) < 6:
                tab = 2
            text += f"{title.text}: " + "\t" * tab + f"{desc.text}\n"
        return text
    return f'Day not valid {day}'


@bot.command()
async def homework(ctx):
    text = ''
    channels = FileManager.get_channels(ctx.guild.name)
    if ctx.channel.id in list(channels.values()):
        channel = list(channels.keys())[list(channels.values()).index(ctx.channel.id)]
    else:
        channel = None
    hws = cm.get_homework(ctx.guild.name, channel)
    if hws:
        for hw in hws:
            text += f"__{hw['channel'].capitalize()}__: **{hw['title']}** ({hw['end_time'].strftime('%d-%m-%y %H:%M')})\n"
        await ctx.send(text[:-1])
    else:
        await ctx.send("There is no homework. :partying_face:")


bot.run(TOKEN)
