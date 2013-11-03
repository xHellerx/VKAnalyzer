import sys
import urllib.request
import json
import pickle
import math
from threading import Thread

def common():
    x = read_uid('Первый пользователь: ')
    y = read_uid('Второй пользователь: ')
    users = find_common(x, y)
    users_with_friends_num = get_friends_num(users)
    output('{1} {2}: {3}', users_with_friends_num)

def circle():
    x = read_uid('Пользователь: ')
    count = int(input("Сколько друзей выводить: "))
    alg = int(input("Алгоритм (1 - число друзей; 2 - доля друзей; 3 - корневая доля друзей): "))
    user_circle = find_circle(x, count, alg)
    output('{3} {4}: {1}, {2}', user_circle)

def update():
    x = read_uid('Пользователь: ')
    delta = find_friends_diff(x)
    removed = get_friends_num(delta[0])
    print('Удалены из друзей:')
    output('{1} {2} ({3}; uid = {0})', removed)
    added = get_friends_num(delta[1])
    print('Добавлены в друзья:')
    output('{1} {2} ({3}; uid = {0})', added)

def find_common(x, y):
    if not isinstance(x, set):
        x = set(get_friends(x))
    if not isinstance(y, set):
        y = set(get_friends(y))
    return x & y

class FetchCommonFriends(Thread):
    def __init__(self, user, target_friends, commons):
        Thread.__init__(self)
        self.user = user
        self.target_friends = target_friends
        self.commons = commons

    def run(self):
        friends = set(get_friends(self.user[0]))
        self.commons.append((
            self.user[0],
            len(find_common(self.target_friends, friends)),
            len(friends),
            self.user[1],
            self.user[2]
        ))

def find_circle(user, count, alg):
    commons = []
    threads = []
    target_friends = set(get_friends(user))
    for friend in target_friends:
        thread = FetchCommonFriends(friend, target_friends, commons)
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


def find_friends_diff(uid):
    old = get_friends(uid)
    new = get_friends(uid, False)
    deleted = [x for x in old if x not in new]
    added = [x for x in new if x not in old]
    return (deleted, added)

def get_friends(user, use_cache = True):
    if use_cache and user in db['friends']:
        return db['friends'][user]

    result = list(map(
        lambda f: (f['uid'], f['first_name'], f['last_name']),
        request_friends(user, False)
    ))

    db['friends'][user] = result

    return result


class FetchFriendsNum(Thread):
    def __init__(self, user, result):
        Thread.__init__(self)
        self.user = user
        self.result = result

    def run(self):
        uid = self.user[0]
        if uid in db['tuples']:
            output = db['tuples'][uid]
        else:
            output = (
                self.user[0],
                self.user[1],
                self.user[2],
                len(request_friends(self.user[0]))
            )
            db['tuples'][uid] = output
        self.result.append(output)

def output(template, data):
    for record in data:
        print(template.format(*record))

def get_friends_num(users):
    result = []
    threads = []
    for user in users:
        thread = FetchFriendsNum(user, result)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return result

def read_uid(message):
    '''
    Reads user id or name from input
    Returns integer
    Raises an exception if user is not found
    '''
    user = input(message)
    uid = request_uid(user)
    if not uid:
        raise Exception('Пользователь {0} не найден'.format(user))
    return uid

def request_uid(user):
    if user in db['shortnames']:
        return db['shortnames'][user]
    response = request('users.get?uids=' + user)
    db['shortnames'][user] = response and response[0]['uid']
    return db['shortnames'][user]

def request_friends(uid, short_request = True):
    url = 'friends.get?uid=' + str(uid)
    if not short_request:
        url += '&fields=uid,first_name,last_name'
    return request(url)

def request(url):
    if debug: print(url)
    root = 'https://api.vk.com/method/'
    result = urllib.request.urlopen(root + url, None, 10).read().decode('utf-8')
    return json.loads(result).get('response', [])

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

db = { 'shortnames': {}, 'friends': {}, 'tuples': {} }
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
        return
    elif sys.argv[1] == 'common':
        common()
    elif sys.argv[1] == 'circle':
        circle()
    elif sys.argv[1] == 'update':
        update()

    save_db()

if __name__ == "__main__":
    main()
