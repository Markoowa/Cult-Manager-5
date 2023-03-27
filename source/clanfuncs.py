from api_interface import Clans, Players, str_to_dt, dt_to_str
from myfuncs import dmerge, plist
import datetime as dt


def log(msg: str):
    print(f'{dt.datetime.utcnow()} {msg}')


def clan_checkup(data: dict, clan_id: str):
    data['nicks_updated'] = False
    data['request_counter'] = 0
    data['new_ledger_entries'] = []

    update_info(data, clan_id)
    update_chat(data)
    if 'currentQuest' not in data or not ('code' in data['currentQuest'] and 'code' == 404):
        update_current_quest(data)
    if 'availableQuests' not in data or (dt.datetime.utcnow().weekday() == 1 and str_to_dt(data['availableQuestsLastUpdate']).date() != dt.datetime.utcnow().date()):
        update_available_quests(data, shuffled=False)
    quest_management(data)
    joining_fees(data)
    weekly_exp(data)

    del data['new_ledger_entries']
    del data['nicks_updated']


def update_info(data: dict, clan_id: str):
    changes = dmerge(data, Clans.info(clan_id).json()); data['request_counter'] += 1
    for stat in changes['upd']:
        try: log(f'Clan {stat} changed by {changes["upd"][stat]["new"]-changes["upd"][stat]["old"]} (now {changes["upd"][stat]["new"]})')
        except TypeError: log(f'Clan {stat} changed from {changes["upd"][stat]["old"]} to {changes["upd"][stat]["new"]}')
        if stat in ('xp', 'memberCount'):
            update_members(data)
        elif stat in ('gold', 'gems'):
            update_ledger(data)


def update_members(data: dict):
    if 'm' not in data:
        data['m'] = {}
    new = {m['playerId']: m for m in Clans.members(data['id']).json() if m['status'] == 'ACCEPTED'}; data['request_counter'] += 1
    for m_id in list(data['m']):  # Member removal
        if m_id not in new:
            log(f'{data["m"][m_id]["username"]} ({m_id}) has been removed from the clan')
            del data['m'][m_id]
    for m_id in new:
        for stat in list(new[m_id]):  # removing unwanted data from request before saving
            if stat not in ("participateInClanQuests", "username", "xp", "level", ):
                del new[m_id][stat]
        if m_id not in data['m']:  # Member addition
            data['m'][m_id] = new[m_id]
            data['m'][m_id]['unpaid_joining_fee'] = {'since': dt_to_str(dt.datetime.utcnow()), 'paid': 0}
            log(f'{new[m_id]["username"]} ({m_id}) has been added to the clan')
        else:  # Member update
            changes = dmerge(data['m'][m_id], new[m_id])
            for stat in changes['upd']:
                try: log(f'{new[m_id]["username"]}\'s {stat} changed by {changes["upd"][stat]["new"]-changes["upd"][stat]["old"]} (now {changes["upd"][stat]["new"]})')
                except TypeError: log(f'{new[m_id]["username"]}\'s {stat} changed from {changes["upd"][stat]["old"]} to {changes["upd"][stat]["new"]}')
                if stat == 'xp':
                    update_player(data, m_id)
    data['nicks_updated'] = True


def update_player(data: dict, player_id: str):
    if 'p' not in data['m'][player_id]:
        data['m'][player_id]['p'] = {'gameStats': {'achievements': {}}}
    new = Players.by_id(player_id).json(); data['request_counter'] += 1
    if 'gameStats' in data['m'][player_id]['p']:
        new['gameStats']['achievements'] = {a['roleId']: a['points'] for a in new['gameStats']['achievements'] if a['level'] != 9}  # removing unwanted data from request before saving
        changes = dmerge(data['m'][player_id]['p']['gameStats']['achievements'], new['gameStats']['achievements'])
        for stat in changes['upd']:  # Tracking player achievement changes
            log(f'{data["m"][player_id]["username"]}\'s "{stat}" role points changed by {changes["upd"][stat]["new"] - changes["upd"][stat]["old"]} (now {changes["upd"][stat]["new"]})')
        changes = dmerge(data['m'][player_id]['p']['gameStats'], new['gameStats'])
        for stat in changes['upd']:  # Tracking player game stats changes
            if stat != 'achievements':
                log(f'{data["m"][player_id]["username"]}\'s {stat} changed by {changes["upd"][stat]["new"] - changes["upd"][stat]["old"]} (now {changes["upd"][stat]["new"]})')
    for stat in list(new):  # removing unwanted data from request before saving
        if stat not in ('gameStats', ):
            del new[stat]
    changes = dmerge(data['m'][player_id]['p'], new)
    for stat in changes['upd']:  # Tracking player changes
        if stat not in ('gameStats',):
            try: log(f'{data["m"][player_id]["username"]}\'s {stat} changed by {changes["upd"][stat]["new"] - changes["upd"][stat]["old"]} (now {changes["upd"][stat]["new"]})')
            except TypeError: log(f'{data["m"][player_id]["username"]}\'s {stat} changed from {changes["upd"][stat]["old"]} to {changes["upd"][stat]["new"]}')


def update_ledger(data: dict):
    ledger = Clans.ledger(data['id']).json(); data['request_counter'] += 1
    if 'lastLedgerUpdate' not in data: data['lastLedgerUpdate'] = ledger[1]['id']
    for entry in ledger:
        if entry['id'] != data['lastLedgerUpdate']: data['new_ledger_entries'].append(entry)
        else: break
    data['lastLedgerUpdate'] = ledger[0]['id']
    for entry in data['new_ledger_entries'][::-1]:
        if entry['type'] == 'DONATE': change_balance(data, entry['playerId'], 'donate', entry['gold'], entry['gems'])
        elif entry['type'] == 'CLAN_QUEST': update_current_quest(data)
        elif entry['type'] == 'CLAN_QUEST_SHUFFLE': update_available_quests(data, shuffled=True)


def update_chat(data: dict):
    if 'lastChatUpdate' not in data:
        data['lastChatUpdate'] = dt_to_str(dt.datetime.utcnow())
        return 1
    unread_entries = []
    chat = Clans.chat(data['id']).json(); data['request_counter'] += 1
    while True:
        if len(chat) > 0:
            for entry in chat:
                if str_to_dt(entry['date']) > str_to_dt(data['lastChatUpdate']):
                    unread_entries.append(entry)
                else: break
            else:
                chat = Clans.chat(data['id'], chat[-1]['date']).json(); data['request_counter'] += 1
                continue
        break
    if len(unread_entries) > 0:
        data['lastChatUpdate'] = unread_entries[0]['date']
        for entry in unread_entries[::-1]: message_handler(data, entry)


def update_current_quest(data: dict):
    quest = Clans.active_quest(data['id']).json(); data['request_counter'] += 1
    if 'quest' in quest:
        del quest['participants'], quest['claimedTime'], quest['tierStartTime'], quest['quest']['rewards'], quest['quest']['promoImagePrimaryColor'], quest['quest']['promoImageUrl'], quest['quest']['id']
        if 'currentQuest' not in data: data['currentQuest'] = quest
        elif 'code' in data['currentQuest'] and data['currentQuest']['code'] == 404:
            log('Quest was started')
            data['currentQuest'] = quest
        elif 'quest' in data['currentQuest']:
            changes = dmerge(data['currentQuest'], quest)
            for stat in changes['upd']:
                if stat == 'tierEndTime':
                    log(f'Current quest\'s tierEndTime was reduced by {str_to_dt(changes["upd"][stat]["old"])-str_to_dt(changes["upd"][stat]["new"])}, time left: {dt.timedelta(seconds=(str_to_dt(quest["tierEndTime"])-dt.datetime.utcnow()).seconds)}')
                    continue
                elif stat == 'xp':
                    log(f'Current quest\'s xp was changed by {changes["upd"][stat]["new"]-changes["upd"][stat]["old"]} ({round((changes["upd"][stat]["new"]-changes["upd"][stat]["old"])/quest["xpPerReward"]*100, 2)}%), quest progress - {quest["xp"]-quest["xpPerReward"]*quest["tier"]}/{quest["xpPerReward"]} ({round((quest["xp"]-quest["xpPerReward"]*quest["tier"])/quest["xpPerReward"]*100, 2)}%)')
                    continue
                log(f'Current quest\'s {stat} changed from {changes["upd"][stat]["old"]} to {changes["upd"][stat]["new"]}')
    elif 'code' in quest and quest['code'] == 404:
        if 'currentQuest' not in data: data['currentQuest'] = quest
        elif 'quest' in data['currentQuest']:
            log('Quest was finished')
            data['currentQuest'] = quest


def update_available_quests(data: dict, shuffled: bool):
    quests = Clans.available_quests(data['id']).json(); data['request_counter'] += 1
    quests = {quest['promoImageUrl'].split('/')[-1].split('.')[0]: {'id': quest['id'], 'purchasableWithGems': quest['purchasableWithGems']} for quest in quests}
    if 'availableQuests' not in data:
        data['availableQuests'] = quests
        data['availableQuestsLastUpdate'] = dt_to_str(dt.datetime.utcnow())
        return
    if shuffled or list(quests) != list(data['availableQuests']):
        data['availableQuestsLastUpdate'] = dt_to_str(dt.datetime.utcnow())
        data['availableQuests'] = quests


def quest_management(data: dict):
    if 'qm' not in data: data['qm'] = {'state': 'quest'}
    if data['qm']['state'] == 'quest':
        waiting_skipper(data)
        # IF (NO QUEST IN PROGRESS OR LAST STAGE IN PROGRESS) AND IT'S NOT MONDAY
        if (('code' in data['currentQuest'] and data['currentQuest']['code'] == 404) or
            (data['currentQuest']['tier'] == 5 and not data['currentQuest']['quest']['purchasableWithGems'] or
             data['currentQuest']['tier'] == 7 and data['currentQuest']['quest']['purchasableWithGems']) and
                not data['currentQuest']['tierFinished']) and dt.datetime.utcnow().weekday() != 0:
            # IF IT'S TUESDAY, MAKE SURE QUESTS ARE ALREADY UPDATED
            if dt.datetime.utcnow().weekday() != 1 or str_to_dt(data['availableQuestsLastUpdate']).date() == dt.datetime.utcnow().date():
                start_vote(data)
    elif data['qm']['state'] == 'vote':
        count_votes(data)
        if dt.datetime.utcnow() - str_to_dt(data["qm"]["since"]) >= dt.timedelta(hours=12-3*(data['qm']['reminders'])) and data['qm']['reminders'] > 0:
            vote_reminder(data)
        if dt.datetime.utcnow() - str_to_dt(data["qm"]["since"]) >= dt.timedelta(hours=12):
            finish_vote(data)
    elif data['qm']['state'] == 'wait':
        if dt.datetime.utcnow() - str_to_dt(data["qm"]["since"]) >= dt.timedelta(hours=12-3*(data['qm']['reminders'])) and data['qm']['reminders'] > 0:
            quest_reminder(data)
        if dt.datetime.utcnow() - str_to_dt(data["qm"]["since"]) >= dt.timedelta(hours=12):
            start_quest(data)


def waiting_skipper(data: dict):
    if ('code' in data['currentQuest'] and data['currentQuest']['code'] == 404) or not data['currentQuest']['tierFinished']:
        return
    if data['currentQuest']['quest']['purchasableWithGems']:
        bottom_limit_of_time_left_to_skip_in_hours = 36 - (18 * data['gold'] / 100000)
    else:
        bottom_limit_of_time_left_to_skip_in_hours = 48 - (24 * data['gold'] / 100000)
    time_left = str_to_dt(data['currentQuest']['tierEndTime']) - dt.datetime.utcnow()
    if time_left >= dt.timedelta(hours=bottom_limit_of_time_left_to_skip_in_hours):
        Clans.skip_waiting(data['id'])
        send_message(data, 'Quest waiting time has been skipped')


def start_vote(data: dict):
    options = f'\n1. none, shuffle if wins\n'+'\n'.join([str(i+2)+'. '+q+(' (GEM)' if data['availableQuests'][q]['purchasableWithGems'] else '') for i, q in enumerate(list(data['availableQuests']))])+'\n'
    msg = 'Quest vote is started and will end in 12 hours\n' \
          'To vote for option N - donate N gold\n' \
          f'{options}\nVoting for a gem quest obliges you to join it'
    send_message(data, msg)
    data['qm'] = {'state': 'vote', 'since': dt_to_str(dt.datetime.utcnow()), 'votes': {}, 'reminders': 3}


def vote_reminder(data: dict):
    options = f'\n1. none, shuffle if wins\n'+'\n'.join([str(i+2)+'. '+q+(' (GEM)' if data['availableQuests'][q]['purchasableWithGems'] else '') for i, q in enumerate(list(data['availableQuests']))])+'\n'
    msg = f'Quest vote ends in {dt.timedelta(seconds=(dt.timedelta(hours=12) - (dt.datetime.utcnow() - str_to_dt(data["qm"]["since"]))).seconds)}\n' \
          'To vote for option N - donate N gold\n' \
          f'{options}\nVoting for a gem quest obliges you to join it'
    send_message(data, msg)
    data['qm']['reminders'] -= 1


def count_votes(data: dict):
    for entry in data['new_ledger_entries']:
        if entry['type'] == 'DONATE':
            if 1 < entry['gold'] < len(data['availableQuests'])+2:
                data['qm']['votes'][entry['playerId']] = list(data['availableQuests'])[entry['gold']-2]
            elif entry['gold'] == 1:
                data['qm']['votes'][entry['playerId']] = 'none'


def finish_vote(data: dict):
    results, voters = vote_result(data)
    winner, voters = results[0], voters[0]
    if winner != 'none':
        msg = f'Quest "{winner}" won the vote, the quest will be started in 12 hours'
        if data['availableQuests'][winner]['purchasableWithGems']: msg += f'\n{plist(voters)} voted for the quest and will either join it or lose 1000 gold from their balances'
        send_message(data, msg)
        data['qm'] = {'state': 'wait', 'since': dt_to_str(dt.datetime.utcnow()), 'voters': voters, 'winner': winner, 'reminders': 3}
    elif dt.datetime.utcnow().weekday() != 0:
        send_message(data, '"none" won the vote, quests will be shuffled and vote restarted')
        data['qm'] = {'state': 'quest'}
        shuffle_quests(data)
    else:
        send_message(data, '"none" won the vote, clan will now wait for automatic quest shuffle (on UTC Tuesday)')
        data['qm'] = {'state': 'quest'}


def shuffle_quests(data: dict):
    disabled = []
    for m_id in data['m']:
        if data['m'][m_id]['participateInClanQuests']:
            Clans.set_participation(data['id'], m_id, False); data['request_counter'] += 1
            disabled.append(m_id)
    Clans.shuffle_quests(data['id']); data['request_counter'] += 1
    for m_id in disabled:
        Clans.set_participation(data['id'], m_id, True); data['request_counter'] += 1


def vote_result(data: dict):
    votes = {}
    for m_id in data['qm']['votes']:
        if m_id in data['m']:
            if data['qm']['votes'][m_id] in votes:
                votes[data['qm']['votes'][m_id]] += 1
            else: votes[data['qm']['votes'][m_id]] = 1
    winners = sorted(votes, key=lambda x: votes[x], reverse=True)
    voters = []
    for winner in winners:
        voters.append([m_id for m_id in data if data[m_id] == winner])
    return winners, voters


def quest_reminder(data: dict):
    okj, oks, off, kick = quest_check(data)
    msg = f'Quest "{data["qm"]["winner"]}" will be started in {dt.timedelta(seconds=(dt.timedelta(hours=12) - (dt.datetime.utcnow() - str_to_dt(data["qm"]["since"]))).seconds)}'
    disabled = []
    kicked = []
    for m_id in data['m']:
        if m_id in off:
            disabled.append(data['m'][m_id]['username'])
        elif m_id in kick:
            kicked.append(data['m'][m_id]['username'])
    if len(disabled) > 0:
        msg += f'\n\n{plist(disabled)} can\'t currently afford joining and will have their quest participation disabled.'
    if len(kicked) > 0:
        msg += f'\n\n{plist(kicked)} can\'t currently afford skipping nor joining and will be kicked.'
    if data['availableQuests'][data["qm"]["winner"]]['purchasableWithGems']:
        must_join_but_unpaid = []
        for m_id in data['qm']['voters']:
            if m_id not in okj: must_join_but_unpaid.append(data['m'][m_id]['username'])
        if len(must_join_but_unpaid) > 0:
            msg += f'\n\n{plist(must_join_but_unpaid)} voted for the gem quest but have yet to pay for joining or enable participation.'
    send_message(data, msg)
    data['qm']['reminders'] -= 1


def start_quest(data: dict):
    okj, oks, off, kick = quest_check(data)
    qt = 'go' if not data['availableQuests'][data["qm"]["winner"]]['purchasableWithGems'] else 'ge'
    msg = f'Quest "{data["qm"]["winner"]}" was started'
    disabled = []
    kicked = []
    for m_id in data['m']:
        if m_id in off:
            disabled.append(data['m'][m_id]['username'])
            change_balance(data, m_id, 'quest skip', -1*data['qc']['s'][qt][0], -1*data['qc']['s'][qt][1])
            Clans.set_participation(data['id'], m_id, False); data['request_counter'] += 1
        elif m_id in kick:
            kicked.append(data['m'][m_id]['username'])
            change_balance(data, m_id, 'quest skip', -1*data['qc']['s'][qt][0], -1*data['qc']['s'][qt][1])
            Clans.set_participation(data['id'], m_id, False); data['request_counter'] += 1
        elif m_id in okj:
            change_balance(data, m_id, 'quest', -1*data['qc']['j'][qt][0], -1*data['qc']['j'][qt][1])
        elif m_id in oks:
            change_balance(data, m_id, 'quest skip', -1*data['qc']['s'][qt][0], -1*data['qc']['s'][qt][1])
    if len(disabled) > 0:
        msg += f'\n\n{plist(disabled)} couldn\'t afford joining and had their quest participation disabled.'
    if len(kicked) > 0:
        msg += f'\n\n{plist(kicked)} couldn\'t afford skipping nor joining and should now be kicked.'
    if data['availableQuests'][data["qm"]["winner"]]['purchasableWithGems']:
        must_join_but_unpaid = []
        for m_id in data['qm']['voters']:
            if m_id not in okj:
                must_join_but_unpaid.append(data['m'][m_id]['username'])
                change_balance(data, m_id, 'voted quest not joined', -1000)
        if len(must_join_but_unpaid) > 0:
            msg += f'\n\n{plist(must_join_but_unpaid)} voted for the gem quest but didn\'t join it and lost 1000 gold from their balances.'
    Clans.buy_quest(data['availableQuests'][data["qm"]["winner"]]['id'], data['id'])
    send_message(data, msg)
    data['qm'] = {'state': 'quest'}


def quest_check(data: dict):
    okj, oks, off, kick = [], [], [], []  # okj - "ok, can join", oks - "ok, can skip"
    qt = 'go' if not data['availableQuests'][data["qm"]["winner"]]['purchasableWithGems'] else 'ge'
    for m_id in data['m']:
        if m_id in data['b']:
            bal = [data['b'][m_id]['go'], data['b'][m_id]['ge']]
        else: bal = [0, 0]
        part = data['m'][m_id]['participateInClanQuests']
        if part:
            if (bal[0] >= data['qc']['j'][qt][0] or data['qc']['j'][qt][0] == 0) and (bal[1] >= data['qc']['j'][qt][1] or data['qc']['j'][qt][1] == 0):
                okj.append(m_id)
            elif (bal[0] >= data['qc']['s'][qt][0] or data['qc']['s'][qt][0] == 0) and (bal[1] >= data['qc']['s'][qt][1] or data['qc']['s'][qt][1] == 0):
                off.append(m_id)
            else: kick.append(m_id)
        elif (bal[0] >= data['qc']['s'][qt][0] or data['qc']['s'][qt][0] == 0) and (bal[1] >= data['qc']['s'][qt][1] or data['qc']['s'][qt][1] == 0):
            oks.append(m_id)
        else: kick.append(m_id)
    return okj, oks, off, kick


def joining_fees(data: dict):
    for entry in data['new_ledger_entries']:
        if entry['type'] == 'DONATE':
            if entry['playerId'] in data['m'] and 'unpaid_joining_fee' in data['m'][entry['playerId']]:
                data['m'][entry['playerId']]['unpaid_joining_fee']['paid'] += entry['gold']
                if data['m'][entry['playerId']]['unpaid_joining_fee']['paid'] >= data['qc']['j']['go'][0]:
                    del data['m'][entry['playerId']]['unpaid_joining_fee']
    for m_id in data['m']:
        if 'unpaid_joining_fee' in data['m'][m_id]:
            if 'kick_announced' not in data['m'][m_id]['unpaid_joining_fee']:
                if dt.datetime.utcnow() - str_to_dt(data['m'][m_id]['unpaid_joining_fee']['since']) > dt.timedelta(hours=1):
                    data['m'][m_id]['unpaid_joining_fee']['kick_announced'] = True
                    send_message(data, f'{id_to_nick(data, m_id)} failed to prepay for joining 1 gold quest within 1 hour of joining the clan and should now be kicked')
            elif data['m'][m_id]['unpaid_joining_fee']['paid'] >= data['qc']['j']['go'][0]:
                del data['m'][m_id]['unpaid_joining_fee']
                send_message(data, f'{id_to_nick(data, m_id)} paid for joining 1 gold quest and is not to be kicked anymore')


def weekly_exp(data: dict):
    if 'lastWeeklyExpCheck' not in data:
        data['lastWeeklyExpCheck'] = dt_to_str(dt.datetime.utcnow())
        for m_id in data['m']:
            data['m'][m_id]['expDuringLastWeeklyCheck'] = data['m'][m_id]['xp']
    if dt.datetime.utcnow() - str_to_dt(data['lastWeeklyExpCheck']) >= dt.timedelta(weeks=1):
        data['lastWeeklyExpCheck'] = dt_to_str(dt.datetime.utcnow())
        punished = []
        for m_id in data['m']:
            if 'expDuringLastWeeklyCheck' in data['m'][m_id]:
                if data['m'][m_id]['xp'] - data['m'][m_id]['expDuringLastWeeklyCheck'] < data['minWeeklyExp']:
                    change_balance(data, m_id, 'weekly exp', -500)
                    punished.append(id_to_nick(data, m_id))
            data['m'][m_id]['expDuringLastWeeklyCheck'] = data['m'][m_id]['xp']
        if len(punished) > 0:
            send_message(data, f'Weekly experience has been controlled, player{"s" if len(punished) != 1 else ""}, who failed to meet the requirement:\n{plist(punished)}\nPunishment is 500 gold deduction from balance.')
        else:
            send_message(data, 'Weekly experience has been controlled, everyone scored enough to avoid punishment.')


def change_balance(data: dict, player_id: str, comment: str, gold: int = 0, gems: int = 0):
    if gold != 0 or gems != 0:
        if player_id not in data['b']: data['b'][player_id] = {'go': 0, 'ge': 0, 'hi': []}
        data['b'][player_id]['go'] += gold; data['b'][player_id]['ge'] += gems
        data['b'][player_id]['hi'].insert(0, f'{dt.datetime.utcnow().strftime("%m.%d")} {curr_to_str(gold, gems)} {comment}')
        if len(data['b'][player_id]['hi']) > 10: data['b'][player_id]['hi'] = data['b'][player_id]['hi'][:10]
    log(f'{id_to_nick(data, player_id)}\'s balance changed by {curr_to_str(gold, gems)} ({comment})')


def curr_to_str(gold: int = 0, gems: int = 0):
    return (((str(gold) + ' gold') if gold else '') +
            (' and ' if gold and gems else '') +
            ((str(gems) + ' gems') if gems else '')
            ) if gold or gems else '0'


def id_to_nick(data: dict, member_id: str):
    if not data['nicks_updated']:
        update_members(data)
        data['request_counter'] += 1
    if member_id in data['m']:
        return data['m'][member_id]['username']
    return f'NOT-CLAN-MEMBER'


def nick_to_id(data: dict, nick: str):
    if not data['nicks_updated']:
        update_members(data)
        data['request_counter'] += 1
    for m_id in data['m']:
        if data['m'][m_id]['username'] == nick:
            return m_id
    return None


def message_handler(data: dict, msg: dict):
    response = ''
    if not msg['isSystem'] and 'playerId' in msg and 'msg' in msg:
        log(f"{id_to_nick(data, msg['playerId'])} says '{msg['msg']}'")
        for submessage in msg['msg'].split(';'):
            submessage = submessage.strip()

            if submessage.split(' ')[0] == '/help':
                if len(submessage.split(' ')) == 1:
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, available commands are:\n" \
                                f"/help (/command), /status, /votes, /balance (nick),\n" \
                                f"/balance_history (nick), /transfer [nick] [gold] [gems],\n" \
                                f"/exp (nick)"
                elif len(submessage.split(' ')) == 2:
                    if submessage.split(' ')[1] == '/status':
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, shows clan quest status, whether vote is in progress or quest is already selected and soon to be started\n"
                    elif submessage.split(' ')[1] == '/votes':
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, counts current votes if quest vote is in progress\n"
                    elif submessage.split(' ')[1] == '/balance':
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, shows your balance in bare \"/balance\" form, or (nick)\'s balance if given. Balance is how much clan owes you, it\'s paid off in form of paid services that are listed in clan description and accumulated with your donations\n"
                    elif submessage.split(' ')[1] == '/balance_history':
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, shows history of changes to your or (nick)\'s balance, maxed at 10 entries\n"
                    elif submessage.split(' ')[1] == '/transfer':
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, transfers [gold] gold and [gems] gems to [nick], gold and gems amounts can be 0\n"
                    elif submessage.split(' ')[1] == '/exp':
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, shows how much clan exp you have earned since the last time it was controlled, how much you have yet to earn and when is the next weekly check\n"
                    else: response += f"⚞{id_to_nick(data, msg['playerId'])}, no info on \"{submessage.split(' ')[1]}\" available\n"
                else: response += f"⚞{id_to_nick(data, msg['playerId'])}, syntax error\n"

            elif submessage.split(' ')[0] == '/balance':
                if len(submessage.split(' ')) == 1:  # own balance
                    if msg['playerId'] in data['b']: balance = curr_to_str(data['b'][msg['playerId']]['go'], data['b'][msg['playerId']]['ge'])
                    else: balance = curr_to_str()
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, your balance is {balance}\n"
                elif len(submessage.split(' ')) == 2:  # someone's else balance
                    player_id = nick_to_id(data, submessage.split(' ')[1])
                    if player_id is not None:
                        if player_id in data['b']: balance = curr_to_str(data['b'][player_id]['go'], data['b'][player_id]['ge'])
                        else: balance = curr_to_str()
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, {submessage.split(' ')[1]}\'s balance is {balance}\n"
                    else: response += f"⚞{id_to_nick(data, msg['playerId'])}, member \"{submessage.split(' ')[1]}\" not found\n"
                else: response += f"⚞{id_to_nick(data, msg['playerId'])}, syntax error\n"

            elif submessage.split(' ')[0] == '/balance_history':
                if len(submessage.split(' ')) == 1:  # own balance history
                    if msg['playerId'] in data['b']: history = '\n'+'\n'.join(data['b'][msg['playerId']]['hi'])
                    else: history = ' empty'
                    while ":P_ID:" in history:
                        index = history.index(":P_ID:")
                        history = history[:index] + id_to_nick(data, history[index+6:index+42]) + history[index+42:]
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, your balance history:{history}\n"
                elif len(submessage.split(' ')) == 2:  # someone's else balance history
                    player_id = nick_to_id(data, submessage.split(' ')[1])
                    if player_id is not None:
                        if player_id in data['b']: history = '\n'+'\n'.join(data['b'][player_id]['hi'])
                        else: history = ' empty'
                        while ":P_ID:" in history:
                            index = history.index(":P_ID:")
                            history = history[:index] + id_to_nick(data, history[index+6:index+42]) + history[index+42:]
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, {submessage.split(' ')[1]}\'s balance history:{history}\n"
                    else: response += f"⚞{id_to_nick(data, msg['playerId'])}, member \"{submessage.split(' ')[1]}\" not found\n"
                else: response += f"⚞{id_to_nick(data, msg['playerId'])}, syntax error\n"

            elif submessage.split(' ')[0] == '/transfer':
                if len(submessage.split(' ')) == 4:
                    receiver_id = nick_to_id(data, submessage.split(' ')[1])
                    if receiver_id is not None:
                        if receiver_id != msg["playerId"]:
                            try:
                                gold, gems = int(submessage.split(' ')[2]), int(submessage.split(' ')[3])
                                if (gold < 0 or gems < 0) and not msg['playerId'] == data["leaderId"]:
                                    response += f"⚞{id_to_nick(data, msg['playerId'])}, can\'t transfer negative values\n"
                                elif (msg['playerId'] not in data['b'] or (gold != 0 and gold > data['b'][msg['playerId']]['go']) or (gems != 0 and gems > data['b'][msg['playerId']]['ge'])) and not msg['playerId'] == data["leaderId"]:
                                    response += f"⚞{id_to_nick(data, msg['playerId'])}, insufficient balance\n"
                                else:
                                    change_balance(data, msg['playerId'], f'to :P_ID:{receiver_id}', -1*gold, -1*gems)
                                    change_balance(data, receiver_id, f'from :P_ID:{msg["playerId"]}', gold, gems)
                                    response += f"⚞{id_to_nick(data, msg['playerId'])}, transferred {curr_to_str(gold, gems)} from your balance to {submessage.split(' ')[1]}\'s\n"
                            except ValueError:
                                response += f"⚞{id_to_nick(data, msg['playerId'])}, invalid values\n"
                        else: response += f"⚞{id_to_nick(data, msg['playerId'])}, can\'t transfer to yourself\n"
                    else: response += f"⚞{id_to_nick(data, msg['playerId'])}, member \"{submessage.split(' ')[1]}\" not found\n"
                else: response += f"⚞{id_to_nick(data, msg['playerId'])}, syntax error\n"

            elif submessage.split(' ')[0] == '/status':
                if data['qm']['state'] == 'wait':
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, waiting for \"{data['qm']['winner']}\" quest to start, time left - {dt.timedelta(seconds=(dt.timedelta(hours=12) - (dt.datetime.utcnow() - str_to_dt(data['qm']['since']))).seconds)}\n"
                elif data['qm']['state'] == 'quest':
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, waiting until a new vote can be started\n"
                elif data['qm']['state'] == 'vote':
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, voting for the next quest, time left - {dt.timedelta(seconds=(dt.timedelta(hours=12) - (dt.datetime.utcnow() - str_to_dt(data['qm']['since']))).seconds)}\n"

            elif submessage.split(' ')[0] == '/exp':
                secs_left = round((dt.timedelta(weeks=1) - (dt.datetime.utcnow() - str_to_dt(data["lastWeeklyExpCheck"]))).total_seconds(), 0)
                days, reminder = divmod(secs_left, 86400)
                hours, reminder = divmod(reminder, 3600)
                minutes, seconds = divmod(reminder, 60)
                until_next = f'{int(days)} days, {int(hours)}:{int(minutes)}:{int(seconds)}'
                if len(submessage.split(' ')) == 1:  # own exp
                    if 'expDuringLastWeeklyCheck' in data['m'][msg['playerId']]:
                        xp = data['m'][msg['playerId']]['xp'] - data['m'][msg['playerId']]['expDuringLastWeeklyCheck']
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, your exp since last weekly check: {xp}/{data['minWeeklyExp']} ({round(xp/data['minWeeklyExp']*100, 2)}%), time left: {until_next}\n"
                    else:
                        response += f"⚞{id_to_nick(data, msg['playerId'])}, you won\'t be controlled on the next weekly exp check, time left: {until_next}\n"
                elif len(submessage.split(' ')) == 2:  # someone's else exp
                    player_id = nick_to_id(data, submessage.split(' ')[1])
                    if player_id is not None:
                        if 'expDuringLastWeeklyCheck' in data['m'][player_id]:
                            xp = data['m'][player_id]['xp'] - data['m'][player_id]['expDuringLastWeeklyCheck']
                            response += f"⚞{id_to_nick(data, msg['playerId'])}, {submessage.split(' ')[1]}\'s exp since last weekly check: {xp}/{data['minWeeklyExp']} ({round(xp/data['minWeeklyExp']*100, 2)}%), time left: {until_next}\n"
                        else:
                            response += f"⚞{id_to_nick(data, msg['playerId'])}, {submessage.split(' ')[1]} won\'t be controlled on the next weekly exp check, time left: {until_next}\n"
                    else: response += f"⚞{id_to_nick(data, msg['playerId'])}, member \"{submessage.split(' ')[1]}\" not found\n"
                else: response += f"⚞{id_to_nick(data, msg['playerId'])}, syntax error\n"

            elif submessage.split(' ')[0] == '/votes':
                if data['qm']['state'] == 'vote':
                    votes = {}
                    for quest in data['qm']['votes'].values():
                        if quest in votes: votes[quest] += 1
                        else: votes[quest] = 1
                    votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
                    conclusion = ''
                    for quest, vote_amount in votes:
                        conclusion += f'{vote_amount} vote{"s" if vote_amount > 1 else ""} for "{quest}"\n'
                    conclusion = conclusion.strip('\n')
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, \n{conclusion}\n"
                else:
                    response += f"⚞{id_to_nick(data, msg['playerId'])}, no vote in progress\n"

            # Leader-only commands
            elif msg['playerId'] == data["leaderId"]:

                if submessage.split(' ')[0] == '/clear_chat':
                    space = "\n"*250
                    for _ in range(30):
                        send_message(data, space)

                elif submessage.split(' ')[0] == '/execute':
                    exec(submessage[9:])

    if len(response) > 0:
        response = response.strip('\n')
        send_message(data, response)


def send_message(data: dict, message: str):
    while len(message) > 250:
        Clans.send_message(data['id'], message[:247]+'...'); data['request_counter'] += 1
        log(f'Sending "{message[:247]+"..."}"')
        message = "..." + message[247:]
    Clans.send_message(data['id'], message); data['request_counter'] += 1
    log(f'Sending "{message}"')
