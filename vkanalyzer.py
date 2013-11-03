import sys
import urllib.request
import json
import pickle
import os
import math
from threading import Thread

def common():
    x = input("Первый пользователь: ")
    y = input("Второй пользователь: ")
    try:
        x = int(x)
    except ValueError: pass
    try:
        y = int(y)
    except ValueError: pass
    if not is_valid_user(x):
        print("Неверный пользователь: " + str(x))
        return
    if not is_valid_user(y):
        print("Неверный пользователь: " + str(y))
        return
    common = find_common(x, y)
    output_friends_numbers(common)

def circle():
    x = input("Пользователь: ")
    try:
        x = int(x)
    except: pass
    count = int(input("Сколько друзей выводить: "))
    alg = int(input("Алгоритм (1 - число друзей; 2 - доля друзей; 3 - корневая доля друзей): "))

    user_circle = find_circle(x, count, alg)
    print(
        '\n'.join(
            map(
                lambda user: '%s %s: %d, %d' % (user[3], user[4], user[1], user[2]),
                user_circle
            )
        )
    )



def update():
    x = input("Пользователь: ")
    try:
        x = int(x)
    except: pass
    delta = find_friends_diff(x)
    print("Удалены из друзей:")
    format_users(delta[0], True)
    print("Добавлены в друзья:")
    format_users(delta[1], True)

def find_common(x, y):
    if not isinstance(x, set):
        x = set(get_friends_tuples(get_uid(x)))
    if not isinstance(y, set):
        y = set(get_friends_tuples(get_uid(y)))
    return x & y

class FetchFriendsCircle(Thread):
    def __init__(self, user, orig_users_list, result):
        Thread.__init__(self)
        self.user = user
        self.orig_users_list = orig_users_list
        self.result = result

    def run(self):
        friends = set(get_friends_tuples(self.user[0]))
        self.result.append((
            self.user[0],
            len(find_common(self.orig_users_list, friends)),
            len(friends),
            self.user[1],
            self.user[2]
        ))

def find_circle(x, count, alg):
    if not is_valid_user(x):
        print("Неверный пользователь: " + str(x))
        return

    commons = []
    threads = []
    x_friends = set(get_friends_tuples(get_uid(x)))
    for y in x_friends:
        thread = FetchFriendsCircle(y, x_friends, commons)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    if alg == 1:
        f = lambda t: -t[1]
    elif alg == 2:
        f = lambda t: -t[1]/(t[2] + 1)
    else:
        f = lambda t: -(t[1]/math.sqrt(t[2] + 1))
    commons = sorted(commons, key = f)
    return commons[:count]


def find_friends_diff(x):
    old = get_friends(x)
    uid = get_uid(x)
    new = request_friends(uid, False)
    deleted = [x for x in old if x not in new]
    added = [x for x in new if x not in old]
    return (deleted, added)


def is_valid_user(x):
    uid = get_uid(x)
    if uid: return True
    if "deactivated" in db["users"][uid]: return False
    return True

def get_friends(user, short_request = False):
    user = get_uid(user)
    if user not in db["users"]: db["users"][user] = {}
    if "deactivated" in db["users"][user]: return set()
    if "friends" in db["users"][user]:
        friends = db["users"][user]["friends"]
    else:
        friends = request_friends(user, short_request)
    return set(friends)


def get_friends_count(user):
    return len(get_friends(user, True))


def format_users(users, show_uid):
    for user in users:
        format_output(user, show_uid)

def fetch_friends(uid, short_request = True):
    url = 'https://api.vk.com/method/friends.get?uid=' + str(uid)
    if not short_request:
        url += '&fields=uid,first_name,last_name'
    result = urllib.request.urlopen(url, None, 10).read().decode('utf-8')
    return json.loads(result).get('response', [])

def get_friends_tuples(user):
    return map(
        lambda f: (f['uid'], f['first_name'], f['last_name']),
        fetch_friends(user, False)
    )

class FetchFriendsNum(Thread):
    def __init__(self, user, result):
        Thread.__init__(self)
        self.user = user
        self.result = result

    def run(self):
        self.result.append({
            'uid': self.user[0],
            'first_name': self.user[1],
            'last_name': self.user[2],
            'friends_num': len(fetch_friends(self.user[0]))
        })

def output_friends_numbers(users):
    '''
    Takes list of users tuples in format:
        (uid, first_name, last_name)
    Prints to the output list of users in format:
        "{first_name} {last_name}: {number of friends}"
    '''
    result = []
    threads = []
    for user in users:
        thread = FetchFriendsNum(user, result)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    print(
        '\n'.join(
            map(
                lambda user: '%s %s: %d' % (user['first_name'], user['last_name'], user['friends_num']),
                result
            )
        )
    )
    print('#########')
    print('total: %d' % len(result))

def format_output(user, show_uid):
    if isinstance(user, tuple):
        data = get_name(user[0])
        data = data[0] + " " + data[1] + " (" + str(get_friends_count(user[0])) + "; " + str(user[1])
    else:
        data = get_name(user)
        data = data[0] + " " + data[1] + " (" + str(get_friends_count(user))
    if show_uid: data += "; uid = " + str(user) + ")"
    print(data)


def get_uid(shortname):
    if not isinstance(shortname, str): return shortname
    if shortname in db["shortnames"]: return db["shortnames"][shortname]
    db["shortnames"][shortname] = request_uid(shortname)
    return db["shortnames"][shortname]

def get_name(user):
    uid = get_uid(user)
    if uid not in db["users"] or "first_name" not in db["users"][uid]:
        request_userinfo(uid)
    return (db["users"][uid]["first_name"], db["users"][uid]["last_name"])


def request_uid(shortname):
    if debug: print("uid requested")
    request = "users.get?uids={uids}"
    request = "https://api.vk.com/method/" + request.format(uids = shortname)
    data = urllib.request.urlopen(request, None, 10)
    data = json.loads(data.read().decode('utf-8'))
    data = data["response"][0]
    cache_usersget(shortname, data)
    return data["uid"]

def request_userinfo(user):
    if debug: print("userinfo requested")
    request_uid(user)

def request_friends(user, short_request):
    if debug: print("friends requested")
    request = "friends.get?uid={uid}"
    if not short_request: request += "&fields={fields}"
    request = "https://api.vk.com/method/" + request.format(
        uid = user, fields = "uid,first_name,last_name")
    if debug: print(request)
    x = urllib.request.urlopen(request, None, 10)
    x = json.loads(x.read().decode('utf-8'))
    if "response" not in x:
        request_userinfo(user)
        db["users"][user]["friends"] = []
        return set()
    x = x["response"]
    if short_request:
        cache_friends(user, x)
        return x
    for t in x:
        cache_usersget(t["uid"], t)
    friends = set(t["uid"] for t in x)
    cache_friends(user, friends)
    return friends

def cache_usersget(user, data):
    if isinstance(user, str):
        db["shortnames"][user] = data["uid"]
        user = data["uid"]
    if user not in db["users"]: db["users"][user] = {}
    for key, value in data.items():
        db["users"][user][key] = value
    save_db()

def cache_friends(uid, friends):
    if uid not in db["users"]: db["users"][uid] = {}
    db["users"][uid]["friends"] = friends
    save_db()

def save_db():
    with open("cache.dat", "wb") as f:
        pickle.dump(db, f)

def load_db():
    global db
    try:
        with open("cache.dat", "rb") as f:
            db = pickle.load(f)
    except FileNotFoundError: pass
    except:
        print("Ошибка базы данных! Напиши об этом Хеллеру."
              "Чтобы программа снова работала попробуй удалить cache.txt")

db = {"shortnames" : {}, "users" : {}}
load_db()

debug = False

def main():
    if len(sys.argv) < 2:
        print(
            'Использование:\n'
            '   `python3 vkanalyzer.py common` для определения общих друзей\n'
            '   `python3 vkanalyzer.py circle` для определения круга общения\n'
            '   `python3 vkanalyzer.py update`, чтобы обновить данные на пользователя и вывести изменения\n'
        )
    elif sys.argv[1] == 'common':
        common()
    elif sys.argv[1] == 'circle':
        circle()
    elif sys.argv[1] == 'update':
        update()

if __name__ == "__main__":
    main()
