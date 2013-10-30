import urllib.request
import json
import pickle
import os
import math

def common():
    x = input("Первый пользователь: ")
    y = input("Второй пользователь: ")
    try:
        x = int(x)
    except: pass
    try:
        y = int(y)
    except: pass
    if not is_valid_user(x):
        print("Неверный пользователь: " + str(x))
        return
    if not is_valid_user(y):
        print("Неверный пользователь: " + str(y))
        return
    format_users(find_common(x, y), False)


def circle():
    x = input("Пользователь: ")
    try:
        x = int(x)
    except: pass
    count = int(input("Сколько друзей выводить: "))
    alg = int(input("Алгоритм (1 - число друзей; 2 - доля друзей; 3 - корневая доля друзей): "))
    format_users(find_circle(x, count, alg), False)


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

def find_common(x, y, short_request = False):
    x = get_friends(x, short_request)
    y = get_friends(y, short_request)
    return x&y

def find_circle(x, count, alg):
    if not is_valid_user(x):
        print("Неверный пользователь: " + str(x))
        return
    friends = get_friends(x, True)
    commons = [(f, len(find_common(x, f, True)), len(get_friends(f, True)))
               for f in friends]
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
    print("Введите команду 'common()' и нажмите Enter для опеределения общих друзей")
    print("Введите команду 'circle()' и нажмие Enter для определения круга общения")
    print("Введите команду 'update()' и нажмите Enter, чтобы обновить данные на пользователя и вывести изменения")

if __name__ == "__main__":
    main()
