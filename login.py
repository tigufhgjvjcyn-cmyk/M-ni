import threading, json, socket, time, datetime, os, traceback
from apic import FreeFireAPI

dd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
up = os.path.join(dd, "saved_token.txt")
os.makedirs(dd, exist_ok=True)

def _ts() -> str:
 n = datetime.datetime.now()
 return f"[{n.day}/{n.month}/{n.year}, {n.hour}:{n.minute}:{n.second}]"

_user_lock = threading.Lock()

TOKEN_FILE = "saved_token.txt"

def _load_users():
    if not os.path.exists(TOKEN_FILE):
        return {}

    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return {u["access_token"]: u for u in data if "access_token" in u}

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}

def _save_users(users):
    tmp = TOKEN_FILE + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    os.replace(tmp, TOKEN_FILE)

def _ensure_user_file():
 if not os.path.exists("saved_token.txt"):
  _save_users({})

_registry: dict = {}
_reg_lock = threading.Lock()


class FreeFireTCP:
 def __init__(self, access_token: str):
  self.access_token = access_token
  self._stop_event  = threading.Event()
  self._socket_lock = threading.Lock()
  self._sock  = None
  self._thread   = None
  self.packetAuth = None
  self.OnlineIP   = None
  self.OnlinePort = None

 def _single_connect(self):
  sock = None
  try:
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   sock.settimeout(10)
   sock.connect((self.OnlineIP, int(self.OnlinePort)))
   with self._socket_lock:
    self._sock = sock
   sock.sendall(self.packetAuth)
   while not self._stop_event.is_set():
    try:
     data = sock.recv(1024)
     if not data: return
    except socket.timeout: return

  except OSError as e:
   print()
  except Exception:
   traceback.print_exc()
  finally:
   with self._socket_lock:
    self._sock = None
   if sock:
    try:
     sock.close()
    except Exception:
     pass

 def _connect_loop(self):
  while not self._stop_event.is_set():
   self._single_connect()

 def _run(self):
  while not self._stop_event.is_set():
   try:
    data = FreeFireAPI().get(self.access_token)
    if data is None or "not" in data:
     self._stop_event.set()
     self._remove_self()
     return
    self.packetAuth = bytes(data["UserAuthPacket"])
    self.OnlineIP   = data["GameServerAddress"]["onlineip"]
    self.OnlinePort = data["GameServerAddress"]["onlineport"]
    self._connect_loop()
   except Exception:
    traceback.print_exc()
    if not self._stop_event.is_set():
     time.sleep(60)

 def _remove_self(self):
  with _reg_lock:
   _registry.pop(self.access_token, None)
  with _user_lock:
   users = _load_users()
   users.pop(self.access_token, None)
   _save_users(users)

 def start(self):
  self._stop_event.clear()
  self._thread = threading.Thread(target=self._run, daemon=True)
  self._thread.start()

 def kill(self):
  self._stop_event.set()
  with self._socket_lock:
   if self._sock:
    try:
     self._sock.shutdown(socket.SHUT_RDWR)
     self._sock.close()
    except Exception:
     pass

 @property
 def is_alive(self) -> bool:
  return not self._stop_event.is_set()

def _restore_users():
 _ensure_user_file()
 with _user_lock:
  users = _load_users()
 for token, info in users.items():
  tcp = FreeFireTCP(token)
  with _reg_lock:
   _registry[token] = {"tcp": tcp}
  tcp.start()
  print(f"{_ts()} [restore] {token}")


def main():
 _restore_users()

 while True:
  os.system("clear")

  print("1. Add Token")
  print("2. Run Saved Token")
  print("3. View Saved Token")
  print("4. Delete Token")
  print("0. Exit")

  choice = input("> ").strip()

  if choice == "1":
   token = input("Access Token: ").strip()

   with _user_lock:
    users = _load_users()
    users[token] = {
     "access_token": token,
     "added": _ts()
    }
    _save_users(users)

   print("Token saved.")
   input()

  elif choice == "2":
   with _user_lock:
    users = _load_users()

   if not users:
    print("No saved token.")
    input()
    continue

   print("\nSaved Tokens:")
   for token in users:
    print(token)

   token = input("\nToken muốn chạy: ").strip()

   if token not in users:
    print("Token not found.")
    input()
    continue

   with _reg_lock:
    if token in _registry:
     print("Already running.")
     input()
     continue

   tcp = FreeFireTCP(token)

   with _reg_lock:
    _registry[token] = {"tcp": tcp}

   tcp.start()

   print("Started.")
   input()

  elif choice == "3":
   with _user_lock:
    users = _load_users()

   if not users:
    print("No saved token.")
   else:
    print("\nSaved Tokens:")
    for token in users:
     print(token)

   input()

  elif choice == "4":
   token = input("Token cần xoá: ").strip()

   with _reg_lock:
    entry = _registry.pop(token, None)

   if entry:
    entry["tcp"].kill()

   with _user_lock:
    users = _load_users()
    users.pop(token, None)
    _save_users(users)

   print("Deleted.")
   input()

  elif choice == "0":
   break

  else:
   print("Invalid choice.")
   input()


if __name__ == "__main__":
    main()