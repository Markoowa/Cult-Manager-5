import json
from time import sleep
from clanfuncs import clan_checkup
from datetime import datetime
import os

with open('../data/clan_id.txt', 'r') as clidfile:
    clan_id = clidfile.read()
data = {}


def load_data():
    try:
        with open('../data/data.json', 'r') as loadfile:
            global data; data = json.load(loadfile)
    except FileNotFoundError:
        data['m'] = {}
        data['b'] = {}
        data['qc'] = {'j': {'go': [500, 0], 'ge': [0, 180]}, 's': {'go': [100, 0], 'ge': [0, 0]}}


def backup():
    with open(f'../data/backups/{(datetime.utcnow()).strftime("%m-%d-%Y-%H-%M-%S")}.json', 'w') as backupfile:
        backupfile.write(json.dumps(data))
    if len(os.listdir('../data/backups')) > 1000:
        do = True
        for file in os.listdir('../data/backups'):
            if do:
                os.remove('../data/backups/' + file)
                do = False
            elif not do:
                do = True


def save_data():
    with open('../data/data.json', 'w') as savefile:
        savefile.write(json.dumps(data))


if __name__ == '__main__':
    while True:
        try:
            load_data()

            clan_checkup(data, clan_id)

            save_data()

            backup()

            sleep(1+data['request_counter'])
        except Exception as err:
            print('im dead', err)
            sleep(3+data['request_counter'])
