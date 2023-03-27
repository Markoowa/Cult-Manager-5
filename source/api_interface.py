import datetime as dt
import requests
import json
from time import sleep

with open('../data/api_key.txt', mode='r') as f:
    API_KEY = f.read()

API_URL = 'https://api.wolvesville.com/'
HEADERS = {"Content-Type": "application/json",
           "Accept": "application/json",
           "Authorization": f'Bot {API_KEY}'}


def generic_request(method: str, endpoint: str, params: dict = None, data: dict = None) -> requests.Response:
    data = json.dumps(data)
    while True:
        try:
            response = requests.request(method, f'{API_URL}{endpoint}', headers=HEADERS, params=params, data=data)
            return response
        except Exception as err:
            print(f'Connection error: {err}, request args: method: {method}, endpoint: {endpoint}, params: {params}, data: {data}, retrying in 5 seconds...')
            sleep(5)


class Items:
    @staticmethod
    def avatar_items() -> requests.Response:
        """Returns all available avatar items, such as hats, shirts, etc."""
        return generic_request('GET', 'items/avatarItems')

    @staticmethod
    def avatar_item_sets() -> requests.Response:
        """Avatar item sets are collections of avatar items and are generally referred to as "outfits" or "skins"."""
        return generic_request('GET', 'items/avatarItemSets')

    @staticmethod
    def avatar_item_collections() -> requests.Response:
        """Returns all collections of single avatar items."""
        return generic_request('GET', 'items/avatarItemCollections')

    @staticmethod
    def profile_icons() -> requests.Response:
        """Returns all available profile icons. Icons in-game are rendered using various icon fonts,
        in most cases Font Awesome."""
        return generic_request('GET', 'items/profileIcons')

    @staticmethod
    def emojis() -> requests.Response:
        """Returns all available emotes. The urlAnimation points to a lottie json file and contains the actual
        animation."""
        return generic_request('GET', 'items/emojis')

    @staticmethod
    def emoji_collections() -> requests.Response:
        """Returns all available emote collections."""
        return generic_request('GET', 'items/emojiCollections')

    @staticmethod
    def backgrounds() -> requests.Response:
        """Returns all available backgrounds. Images have a transparent background. Use backgroundColorDay
        and backgroundColorNight to render the final image.\n
        imageDaySmall and imageNightSmall return the images used in-game. The other images are used for inventory,
        dashboard, etc. In-game images have a smaller resolution and fewer details."""
        return generic_request('GET', 'items/backgrounds')

    @staticmethod
    def loading_screens() -> requests.Response:
        """Returns all available loading screens."""
        return generic_request('GET', 'items/loadingScreens')

    @staticmethod
    def role_icons() -> requests.Response:
        """Returns all available role icons."""
        return generic_request('GET', 'items/roleIcons')

    @staticmethod
    def advanced_role_card_offers() -> requests.Response:
        """Returns all available advanced role card offers. Offers might not be available in the shop and might not
        be purchasable."""
        return generic_request('GET', 'items/advancedRoleCardOffers')

    @staticmethod
    def roses() -> requests.Response:
        """Returns all available roses. SINGLE_ROSE is a single rose that can be sent between two players. SERVER_ROSE
        is a rose bouquet which will send one rose to all players in a game."""
        return generic_request('GET', 'items/roses')

    @staticmethod
    def talismans() -> requests.Response:
        """Returns all available talismans. If a talisman is marked as deprecated that talisman can no longer
        be obtained."""
        return generic_request('GET', 'items/talismans')

    @staticmethod
    def redeem_api_hat() -> requests.Response:
        """Unlocks the API hat for the owner of the bot. Response HTTP code is 204 (no content), regardless of whether
        the owner of the bot already has the API hat or not."""
        return generic_request('POST', 'items/redeemApiHat')


class RoleRotations:
    @staticmethod
    def current_role_rotation() -> requests.Response:
        """Returns current live role rotations. Possible game modes are quick, sandbox, advanced, ranked-league-silver,
        ranked-league-gold and crazy-fun (limited event-like games)."""
        return generic_request('GET', 'roleRotations')


class BattlePass:
    @staticmethod
    def current_season() -> requests.Response:
        """Returns the current battle pass season."""
        return generic_request('GET', 'battlePass/season')

    @staticmethod
    def challenges() -> requests.Response:
        """Returns the currently active battle pass challenges. Challenges typically update every 15 days."""
        return generic_request('GET', 'battlePass/season')


class Shop:
    @staticmethod
    def active_offers() -> requests.Response:
        """Returns the current offers available in the shop. This can change on short notice and players might have
        additional offers active that are only visible for them."""
        return generic_request('GET', 'shop/activeOffers')


class Players:
    @staticmethod
    def by_id(player_id: str) -> requests.Response:
        """Returns the player profile of the player with id playerId. badgeIds and roleCards might be empty if that
        players has chosen to hide this information.\n
        If the field creationTime is not present in the response, that means the player joined some time before 2018-08-03."""
        return generic_request('GET', f'players/{player_id}')

    @staticmethod
    def by_username(username: str) -> requests.Response:
        """Return the player with the given username or throws a 404 error if no player was found."""
        return generic_request('GET', f'players/search?username={username}')


class Clans:
    @staticmethod
    def search(name: str, join_type: str = None, language: str = None, not_full: bool = None, exact_name: bool = None,
               min_level_min: int = None, min_level_max: int = None, sort_by: str = None) -> requests.Response:
        """Returns a list of clans matching name (case-insensitive!). Additional query parameters are:\n
        joinType: one of PUBLIC, PRIVATE and JOIN_BY_REQUEST\n
        language: 2 letter language code\n
        notFull: boolean\n
        exactName: boolean, if true will return only clans which exactly match the name\n
        minLevelMin: number\n
        minLevelMax: number\n
        sortBy: one of XP, CREATION_TIME, QUEST_HISTORY_COUNT, NAME, MIN_LEVEL"""
        params = {}
        if join_type is not None:
            params['joinType'] = join_type
        if language is not None and len(language) == 2:
            params['language'] = language
        if not_full is not None:
            params['notFull'] = not_full
        if exact_name is not None:
            params['exactName'] = exact_name
        if min_level_min is not None:
            params['minLevelMin'] = min_level_min
        if min_level_max is not None:
            params['minLevelMax'] = min_level_max
        if sort_by is not None:
            params['sortBy'] = sort_by
        return generic_request('GET', f'clans/search?name={name}', params=params)

    @staticmethod
    def info(clan_id: str) -> requests.Response:
        """Returns the public info about the clan with id clanId. The fields gold and gems are only available for bots
        that have been added to this clan."""
        return generic_request('GET', f'clans/{clan_id}/info')

    @staticmethod
    def members(clan_id: str) -> requests.Response:
        """Returns a list of all members in this clan. The fields joinMessage, participateInClanQuests and players with
        a status other than ACCEPTED are only available for bots that have been added to this clan."""
        return generic_request('GET', f'clans/{clan_id}/members')

    @staticmethod
    def member(clan_id: str, member_id: str) -> requests.Response:
        """Returns a single member belonging to a clan."""
        return generic_request('GET', f'clans/{clan_id}/members/{member_id}')

    @staticmethod
    def set_participation(clan_id: str, member_id: str, new_value: bool) -> requests.Response:
        """Changes if the member with the id memberId will participate in the next clan quest. Request returns the
        modified clan member."""
        return generic_request('PUT', f'clans/{clan_id}/members/{member_id}/participateInQuests',
                               data={'participateInQuests': new_value})

    @staticmethod
    def chat(clan_id: str, last_date: str = None) -> requests.Response:
        """Returns the last chat messages of a clan chat. The last_date argument can be used to paginate
        through older messages."""
        if last_date is None:
            return generic_request('GET', f'clans/{clan_id}/chat')
        return generic_request('GET', f'clans/{clan_id}/chat', params={'oldest': last_date})

    @staticmethod
    def send_message(clan_id: str, message: str) -> requests.Response:
        """Send a message to the clan chat."""
        return generic_request('POST', f'clans/{clan_id}/chat', data={'message': message})

    @staticmethod
    def ledger(clan_id: str) -> requests.Response:
        """Returns the clan ledger. type can be one of CREATE_CLAN, DONATE, CLAN_QUEST, CLAN_ICON, CLAN_QUEST_SHUFFLE,
        CLAN_QUEST_SKIP_WAIT or CLAN_QUEST_CLAIM_TIME."""
        return generic_request('GET', f'clans/{clan_id}/ledger')

    @staticmethod
    def logs(clan_id: str) -> requests.Response:
        """Returns the most recent clan log entries. action can be one of\n
        BLACKLIST_ADDED\n
        BLACKLIST_REMOVED\n
        JOIN_REQUEST_SENT_BY_CLAN\n
        JOIN_REQUEST_SENT_BY_EXTERNAL_PLAYER: an external player sent a request to join this clan\n
        JOIN_REQUEST_ACCEPTED\n
        JOIN_REQUEST_DECLINED_BY_CLAN: leader / co-leader decline the request\n
        JOIN_REQUEST_DECLINED_BY_EXTERNAL_PLAYER: external player declined an invitation to join\n
        JOIN_REQUEST_WITHDRAWN\n
        LEADER_CHANGED\n
        CO_LEADER_PROMOTED\n
        CO_LEADER_DEMOTED\n
        CO_LEADER_RESIGNED\n
        PLAYER_LEFT\n
        PLAYER_KICKED\n
        PLAYER_JOINED\n
        PLAYER_QUEST_PARTICIPATION_ENABLED\n
        PLAYER_QUEST_PARTICIPATION_DISABLED\n
        Each entry will either have playerId + playerUsername or playerBotId + playerBotOwnerUsername defined depending
        on who initiated the action."""
        return generic_request('GET', f'clans/{clan_id}/logs')

    @staticmethod
    def available_quests(clan_id: str) -> requests.Response:
        """Returns all quests that are currently available for purchase for this clan."""
        return generic_request('GET', f'clans/{clan_id}/quests/available')

    @staticmethod
    def shuffle_quests(clan_id: str) -> requests.Response:
        """Shuffles the currently available quests for this clan."""
        return generic_request('POST', f'clans/{clan_id}/quests/available/shuffle')

    @staticmethod
    def buy_quest(quest_id: str, clan_id: str) -> requests.Response:
        """Claims a quests for this clan if none is active."""
        return generic_request('POST', f'clans/{clan_id}/quests/claim', data={'questId': quest_id})

    @staticmethod
    def active_quest(clan_id: str) -> requests.Response:
        """Returns the currently active quest for this clan if available."""
        return generic_request('GET', f'clans/{clan_id}/quests/active')

    @staticmethod
    def skip_waiting(clan_id: str) -> requests.Response:
        """Skips the waiting time for the active clan quest."""
        return generic_request('POST', f'clans/{clan_id}/quests/active/skipWaitingTime')

    @staticmethod
    def claim_more_time(clan_id: str) -> requests.Response:
        """Claims additional time for the active clan quests. Can only be called once per stage."""
        return generic_request('POST', f'clans/{clan_id}/quests/active/claimTime')

    @staticmethod
    def cancel_quest(clan_id: str) -> requests.Response:
        """Cancels the active quest for this clan and refunds a small amount of the initial costs."""
        return generic_request('POST', f'clans/{clan_id}/quests/active/cancel')

    @staticmethod
    def quest_history(clan_id: str) -> requests.Response:
        """Returns the list of all quests this clan has done in the past."""
        return generic_request('GET', f'clans/{clan_id}/quests/history')

    @staticmethod
    def all_quests() -> requests.Response:
        """Returns all clan quests, regardless of if they can be bought."""
        return generic_request('GET', f'clans/quests/all')

    @staticmethod
    def authorized() -> requests.Response:
        """Returns a list of clans where this bot has been added to. If the list is empty, this bot has not been added
        to any clan. Only leads can add a bot to a clan."""
        return generic_request('GET', f'clans/authorized')


def str_to_dt(string: str) -> dt.datetime:
    return dt.datetime.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ')


def dt_to_str(date: dt.datetime) -> str:
    return dt.datetime.strftime(date, '%Y-%m-%dT%H:%M:%S.%fZ')


if __name__ == '__main__':
    from pprint import pprint
    pprint(Clans.available_quests('87c636c9-8e27-401d-a8bc-426aff2eceea').json())

