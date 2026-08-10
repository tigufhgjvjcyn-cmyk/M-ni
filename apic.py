import requests, json, base64, time, struct, datetime, re, os, string, threading
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from typing import Dict, Any, Optional, Tuple, Union, TypedDict, List
from dataclasses import dataclass
from enum import IntEnum

from protobuf_decoder.protobuf_decoder import Parser
def parse_results(parsed_results):
 result_dict = {}
 for result in parsed_results:
  if result.field not in result_dict:
   result_dict[result.field] = []
  field_data = {}
  if result.wire_type in ["varint", "string", "bytes"]:
   field_data = result.data
  elif result.wire_type == "length_delimited":
   field_data = parse_results(result.data.results)
  result_dict[result.field].append(field_data)
 return {
  key: value[0] if len(value) == 1
  else value for key, value in result_dict.items()
  }

protobuf_dec = lambda data: json.dumps(parse_results(
 Parser().parse(data)
 ), ensure_ascii=False)
def Encrypt(value):
 value = int(value)
 result = []
 while value > 0x7F:
  result.append((value & 0x7F) | 0x80)
  value >>= 7
 result.append(value)
 return bytes(result)

def Decrypt(value):
 result, shift = 0, 0
 for byte in bytes.fromhex(value):
  result |= (byte & 0x7F) << shift
  if not (byte & 0x80):
   break
  shift += 7
 return result

def AES_CBC128(data, key, iv):
 cipher = AES.new(key, AES.MODE_CBC, iv)
 return cipher.encrypt(pad(data, 0x10))

def create_varint_field(field_number, value):
 field_header = (field_number << 3) | 0
 return Encrypt(field_header) + Encrypt(value)

def create_length_delimited_field(field_number, value):
 field_header = (field_number << 3) | 2
 encoded_value = value.encode() if isinstance(value, str) else value
 return Encrypt(field_header) + Encrypt(len(encoded_value)) + encoded_value

def pb_encode(fields):
 packet = bytearray()
 for field, value in fields.items():
  field = int(field)
  if isinstance(value, list):
   for item in value:
    if isinstance(item, dict):
     packet.extend(create_length_delimited_field(field, pb_encode(item)))
  elif isinstance(value, dict):
   nested_packet = pb_encode(value)
   packet.extend(create_length_delimited_field(field, nested_packet))
  elif isinstance(value, int):
   packet.extend(create_varint_field(field, value))
  elif isinstance(value, str) or isinstance(value, bytes):
   packet.extend(create_length_delimited_field(field, value))
 return bytes(packet)


class ProtoBuf:
 def __init__(self, data):
  self.data = data

 def varint(self, buffer: bytes, pos: int = 0) -> Tuple[int, int]:
  result, shift = 0, 0
  while shift < 64 and pos < len(buffer):
   byte = buffer[pos]
   pos += 1
   result |= (byte & 0x7F) << shift
   if not (byte & 0x80):
    return result, pos
   shift += 7
  return result, pos

 def repeated(self, data: bytes) -> List[int]:
  pos, out = 0, []
  while pos < len(data):
   val, pos = self.varint(data, pos)
   out.append(val)
  return out

 def string(self, buffer: bytes, pos: int) -> Tuple[str, int]:
  length, pos = self.varint(buffer, pos)
  newpos = min(pos + length, len(buffer))
  value = buffer[pos:newpos]
  try: value = value.decode("utf-8")
  except: pass
  return value, newpos

 def fixed32(self, buffer: bytes, pos: int) -> Tuple[int, int]:
  return (struct.unpack("<I", buffer[pos:pos + 4])[0], pos + 4) if pos + 4 <= len(buffer) else (0, pos)

 def fixed64(self, buffer: bytes, pos: int) -> Tuple[int, int]:
  return (struct.unpack("<Q", buffer[pos:pos + 8])[0], pos + 8) if pos + 8 <= len(buffer) else (0, pos)

 def parse_field(self, buffer: bytes, pos: int) -> Tuple[int, Any, int]:
  if pos >= len(buffer): return 0, None, pos
  key, pos = self.varint(buffer, pos)
  field_number, wire_type = key >> 3, key & 0x7
  try:
   if wire_type == 0: value, pos = self.varint(buffer, pos)
   elif wire_type == 1: value, pos = self.fixed64(buffer, pos)
   elif wire_type == 2: value, pos = self.string(buffer, pos)
   elif wire_type == 5: value, pos = self.fixed32(buffer, pos)
   else: return field_number, None, pos
  except (struct.error, IndexError):
   return field_number, None, pos
  return field_number, value, pos

 def protobuf(self, buffer: Optional[bytes] = None, offset: int = 0) -> Dict[str, Any]:
  if buffer is None:
   buffer = self.data
  result = {}
  while offset < len(buffer):
   field_number, value, offset = self.parse_field(buffer, offset)
   if isinstance(value, bytes) and value:
    try:
     nested = self.protobuf(value)
     if nested: value = nested
    except: pass
   key = str(field_number)
   result.setdefault(key, []).append(value)
  return {k: v[0] if len(v) == 1 else v for k, v in result.items()}

 def fieldsRaw(self, buf: bytes, pos: int) -> Tuple[int, int, bytes, int, int]:
  start = pos
  key, pos = self.varint(buf, pos)
  num, wt = key >> 3, key & 0x7
  if wt == 0: _, end = self.varint(buf, pos)
  elif wt == 1: end = pos + 8
  elif wt == 2:
   length, lp = self.varint(buf, pos)
   end = lp + length
  elif wt == 5: end = pos + 4
  else: return num, wt, b'', pos, pos
  return num, wt, buf[start:end], pos, end

 def EXTRACT_FIELDS(self, fields: List[int], mode: str = "repeated") -> List:
  cur = self.data
  for depth, target in enumerate(fields):
   pos = 0; found = False
   if depth == len(fields) - 1:
    results = []
    while pos < len(cur):
     num, wt, raw, val_start, val_end = self.fieldsRaw(cur, pos)
     if num == target:
      if mode == "repeated":
       if wt == 0:
        val, _ = self.varint(cur, val_start)
        results.append(val)
       elif wt == 2:
        _, lp = self.varint(cur, val_start)
        packed = cur[lp:val_end]
        results += self.repeated(packed)
      elif mode == "bytes":
       if wt == 2:
        _, lp = self.varint(cur, val_start)
        results.append(cur[lp:val_end])
       else:
        results.append(cur[val_start:val_end])
     pos = val_end
    if len(results) == 0: return []
    if len(results) == 1: return results[0]
    return results
   else:
    while pos < len(cur):
     num, wt, raw, val_start, val_end = self.fieldsRaw(cur, pos)
     if num == target and wt == 2:
      _, lp = self.varint(cur, val_start)
      cur = cur[lp:val_end]
      found = True; break
     pos = val_end
    if not found: return []
  return []


class gayerr(Exception): pass
@dataclass
class account_data:
 access_token = ""
 open_id = ""
 platform = 0x4
 login_platform = 0x4
 main_active_platform = 0x4
 chat_ip = chat_port = online_ip = online_port  = ""
 create_time = None
 expiry_time = None
 guild_id = None
 guild_code = None
 login_token  = None
 account_id = None
 base_url = None
 login_time = None
 key = None
 iv = None


class gringay:
 @staticmethod
 def tokendecode(token):
  try:
   parts = token.split(".")
   if len(parts) != 3: raise gayerr("Invalid token format")
   payload = parts[1]
   payload += "=" * (0x4 - len(payload) % 0x4)
   return json.loads(base64.urlsafe_b64decode(payload).decode('utf-8'))
  except (ValueError, json.JSONDecodeError) as e: pass
 
 @staticmethod
 def format_timestamp(timestamp):
  if timestamp is None: return ""
  return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp))

def storeApps(package):
 I=requests.get(f"https://play.google.com/store/apps/%s"%package)
 I=re.search(r'\[\[\["(\d+\.\d+\.\d+)"\]\]', I.text)
 if I:return I.group(1)
 return None

def bdversion(ver:str=storeApps("details?id=com.dts.freefireth")):
 if not ver:ver=storeApps("details?id=com.dts.freefireth")
 I="https://version.common.redflamenco.com/live/ver.php{}"
 II="?version=%s&lang=vi&device=android&region=VN" % ver
 res=requests.get(I.format(II))
 return res.json()





detail_vers = bdversion()
print(detail_vers["remote_version"], detail_vers["latest_release_version"], detail_vers["server_url"])
class APIClient:
 def __init__(self):
  self._data = account_data()
  self.is_emulator = False
  self.language = "vn"
  self.base_url = detail_vers["server_url"]
  self.client_version = detail_vers["remote_version"]
  self.release_version = detail_vers["latest_release_version"]
  self.key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
  self.iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
  self.session = requests.Session()

  self.session.headers.update({'Authorization': 'Bearer', 'X-Ga': 'v1 1', 'X-Unity-Version': '2022.3.47f1', 'Content-Type': 'application/x-www-form-urlencoded', 'Releaseversion': self.release_version, 'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)', 'Accept': '*/*', 'Accept-Encoding': 'gzip, br', 'Cf-Visitor': '{"scheme":"https"}'})

 def auth_guest_token(self, uid, password):
  payload = {
   "uid": str(uid), "password": str(password),
   "response_type": "token", "client_type": "2", "client_id": "100067", 
   "client_secret": bytes([50, 101, 101, 52, 52, 56, 49, 57, 101, 57, 98, 52, 53, 57, 56, 56, 52, 53, 49, 52, 49, 48, 54, 55, 98, 50, 56, 49, 54, 50, 49, 56, 55, 52, 100, 48, 100, 53, 100, 55, 97, 102, 57, 100, 56, 102, 55, 101, 48, 48, 99, 49, 101, 53, 52, 55, 49,53, 98, 55, 100, 49, 101, 51]).decode()
   }
  try:
   data = requests.post(
    "https://auth.garena.com/oauth/guest/token/grant",
    data=payload,
    headers={
     "Accept-Encoding": "gzip", "Accept-Encoding": "gzip, deflate",
     "Content-Type": "application/x-www-form-urlencoded",
     "User-Agent": "Mozilla/5.0 (Android 9; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0",
     }
    ).json()
   if "access_token" not in data: return "account not found"
   self._data.access_token = data["access_token"]
   self._data.open_id = data["open_id"]
   self._data.platform = data.get("platform", 0x4)
   self._data.login_platform = data.get("login_platform", 0x4)
   self._data.main_active_platform = data.get("main_active_platform")
   self._data.create_time = data.get("create_time")
   self._data.expiry_time = data.get("expiry_time")
  except Exception as e: print(e)

 def auth_token_inspect(self, access_token):
  try:
   data = requests.get(
    "https://auth.garena.com/oauth/token/inspect",
    params={"token": access_token}
    ).json()
   if "open_id" not in data: raise gayerr("Invalid access token")
   self._data.access_token = access_token
   self._data.open_id = data["open_id"]
   self._data.platform = data.get("platform", 0x4)
   self._data.login_platform = data.get("login_platform", 0x4)
   self._data.main_active_platform = data.get("main_active_platform")
   self._data.create_time = data.get("create_time")
   self._data.expiry_time = data.get("expiry_time")
  except Exception as e: pass

 def MajorLogin(self):
  fields = {'10': b'Viettel',
 '100': str(self._data.login_platform),
 '102': b'D\\\x16A\x02T\rV8',
 '11': b'WIFI',
 '12': 1666,
 '13': 750,
 '14': b'480',
 '15': b'ARM64 FP ASIMD AES | 2000 | 8',
 '16': 7535,
 '17': b'Mali-G57 MC3',
 '18': b'OpenGL ES 3.2 v1.r32p1-01eac0.461cd25a1c7796cc6d3ad05234c053ac',
 '19': b'Google|fe4ce5a1-a190-41ab-82c8-03480f84a055',
 '20': b'123.200.200.200',
 '21': b'vn',
 '22': self._data.open_id,
 '23': str(self._data.main_active_platform),
 '24': b'Handheld',
 '25': b'OPPO CPH2161',
 '26': b'VN',
 '29': self._data.access_token,
 '3': time.strftime("%Y-%m-%d %H:%M:%S"),
 '30': 1,
 '4': b'free fire',
 '41': b'Viettel',
 '42': b'WIFI',
 '5': 1,
 '57': b'7428b253defc164018c604a1ebbfebdf',
 '60': 111125,
 '61': 24794,
 '62': 646,
 '64': 25013,
 '65': 111125,
 '66': 25013,
 '67': 111125,
 '7': self.client_version,
 '73': 1,
 '74': b'/data/app/~~n7knmMB01-DLeDewi_wxUg==/com.dts.freefireth-VuCf1iCq4HpR'
       b'eALgdQ_S8A==/lib/arm64',
 '76': 1,
 '77': b'4c322aeb56444feaa151d1ea91a8f7f2|/data/app/~~n7knmMB01-DLeDewi_wxUg='
       b'=/com.dts.freefireth-VuCf1iCq4HpReALgdQ_S8A==/base.apk',
 '78': 3,
 '79': 2,
 '8': b'Android OS 12 / API-31 (SP1A.210812.016/Q.GDPR.202206202156)',
 '81': b'64',
 '83': b'2019120776',
 '85': 3,
 '86': b'OpenGLES2',
 '87': 4095,
 '88': 8,
 '9': b'Handheld',
 '92': 5131,
 '93': b'android',
 '94': b'KqsHT5IZGShh357jM5Y3aYhz8HebbInIx4a+YqQHn93f9Reo3WlXAjYW6pc3yDbOvez9'
       b'b4ddq4HBemChGvGgZ3iWLAk=',
 '95': 111207,
 '96': b'{"cur_rate":[60,90],"support_etc2":false}',
 '97': 1,
 '99': str(self._data.platform)}

  try:
   response = self.session.post(
    "%sMajorLogin" % self.base_url,
    data = AES_CBC128(
     pb_encode(fields),
     self.key, self.iv
    )
   )
   pb = ProtoBuf(response.content)
   res = pb.protobuf()
   self._data.account_id = res.get("1")
   self._data.server = res.get("3")
   self._data.login_token = res.get("8")
   self._data.base_url = res.get("10")
   self._data.login_time = res.get("21")
   self._data.key = pb.EXTRACT_FIELDS([22], mode="bytes")
   self._data.iv = pb.EXTRACT_FIELDS([23], mode="bytes")
  except Exception as e: print(2, e)

 def GetLoginData(self):
  try:
   fields = {'10': b'Viettel',
 '100': str(self._data.login_platform),
 '102': b'D\\\x16A\x02T\rV8',
 '11': b'WIFI',
 '12': 1666,
 '13': 750,
 '14': b'480',
 '15': b'ARM64 FP ASIMD AES | 2000 | 8',
 '16': 7535,
 '17': b'Mali-G57 MC3',
 '18': b'OpenGL ES 3.2 v1.r32p1-01eac0.461cd25a1c7796cc6d3ad05234c053ac',
 '19': b'Google|fe4ce5a1-a190-41ab-82c8-03480f84a055',
 '20': b'171.245.232.205',
 '21': b'vn',
 '22': self._data.open_id,
 '23': str(self._data.main_active_platform),
 '24': b'Handheld',
 '25': b'OPPO CPH2161',
 '26': b'VN',
 '29': self._data.access_token,
 '3': time.strftime("%Y-%m-%d %H:%M:%S"),
 '30': 1,
 '4': b'free fire',
 '41': b'Viettel',
 '42': b'WIFI',
 '5': 1,
 '57': b'7428b253defc164018c604a1ebbfebdf',
 '60': 111125,
 '61': 24794,
 '62': 646,
 '64': 25013,
 '65': 111125,
 '66': 25013,
 '67': 111125,
 '7': self.client_version,
 '73': 1,
 '74': b'/data/app/~~n7knmMB01-DLeDewi_wxUg==/com.dts.freefireth-VuCf1iCq4HpR'
       b'eALgdQ_S8A==/lib/arm64',
 '76': 1,
 '77': b'4c322aeb56444feaa151d1ea91a8f7f2|/data/app/~~n7knmMB01-DLeDewi_wxUg='
       b'=/com.dts.freefireth-VuCf1iCq4HpReALgdQ_S8A==/base.apk',
 '78': 3,
 '79': 2,
 '8': b'Android OS 12 / API-31 (SP1A.210812.016/Q.GDPR.202206202156)',
 '81': b'64',
 '83': b'2019120776',
 '85': 3,
 '86': b'OpenGLES2',
 '87': 4095,
 '88': 8,
 '9': b'Handheld',
 '92': 5131,
 '93': b'android',
 '94': b'KqsHT5IZGShh357jM5Y3aYhz8HebbInIx4a+YqQHn93f9Reo3WlXAjYW6pc3yDbOvez9'
       b'b4ddq4HBemChGvGgZ3iWLAk=',
 '95': 111207,
 '96': b'{"cur_rate":[60,90],"support_etc2":false}',
 '97': 1,
 '99': str(self._data.platform)}
   response = self.session.post(
     "%s/GetLoginData" % self._data.base_url,
     headers = {
      "Authorization": "Bearer %s" % self._data.login_token,
      "Host": self._data.base_url[8:]
      }, data = AES_CBC128(
      pb_encode(fields),
      self.key, self.iv
     )
    )
   data = json.loads(protobuf_dec(response.content.hex()))
   self.logindata = data
   self._data.guild_id = data.get("20")
   self._data.guild_code = data.get("55")
   sv, chat = data.get("14"), data.get("32")
   if len(chat) > 6: self._data.chat_port, self._data.chat_ip = chat[-5:], chat[:-6]
   if len(sv) > 6: self._data.online_port, self._data.online_ip = sv[-5:], sv[:-6]
  except Exception as e: print(1, e)

 def TAO_PACKET_XT(self) -> str:
  try:
   esid = lambda rec: (
    lambda s: s[rec.upper()] if rec.upper() in s else None)(
     {x["2"].upper(): x["1"] for x in self.logindata["19"]}
    )
   eid = hex(self._data.account_id)[2:]
   bytestoken = self._data.login_token.encode()
   encrypts = AES_CBC128(bytestoken, self._data.key, self._data.iv).hex()
   lengths = hex(len(encrypts) // 2)[2:]
   header = ("0" * 16)[:max(0, 16 - len(eid))]
   packet = "%s%s%s%X%05d%s%s" % (
     "%02d%02X" % (1, esid(self._data.server)), header,
     eid, self._data.login_time, 0x0, lengths, encrypts
    )
   return bytes.fromhex(packet)
  except Exception as e: print(e)

 def auth(self, access_token, is_emulator = False):
  try:
   self.is_emulator = is_emulator
   if ":" in access_token:
    uid, password = access_token.split(":")
    self.auth_guest_token(int(uid), password)
   else: self.auth_token_inspect(access_token)
   self.MajorLogin()
   self.GetLoginData()
   return self._build_api_response(self.TAO_PACKET_XT())
  except Exception as e: pass
 
 def _build_api_response(self, authpacket):
  if not self._data.login_token: return "account not found"
  data = gringay.tokendecode(self._data.login_token)
  if self._data.guild_id:
   guild = {}
   guild["id"] = self._data.guild_id
   guild["secret_code"] = self._data.guild_code
  else: guild = False

  saddress = {}
  saddress["chatip"] = self._data.chat_ip
  saddress["chatport"] = self._data.chat_port
  saddress["onlineip"] = self._data.online_ip
  saddress["onlineport"] = self._data.online_port
  
  response = {}
  response["CreateTime"] = gringay.format_timestamp(self._data.create_time)
  response["ExpiryTime"] = gringay.format_timestamp(self._data.expiry_time)
  response["UserAuthPacket"] = list(authpacket)
  response["UserAuthToken"] = self._data.login_token
  response["UserNickName"] = data.get("nickname")
  response["UserAccountUID"] = data.get("account_id")
  response["LockRegion"] = data.get("lock_region")
  response["ClientVersion"] = data.get("client_version")
  response["IsEmulator"] = data.get("is_emulator")
  response["GuildData"] = guild
  response["BaseUrl"] = self._data.base_url or ""
  response["key"] = list(self._data.key)
  response["iv"] = list(self._data.iv)
  response["logindata"] = self.logindata
  response["GameServerAddress"] = saddress
  return response

class FreeFireAPI: 
 def __init__(self):
  self.client = APIClient()
 def get(self, target: str, is_emulator: bool = False):
  return self.client.auth(target, is_emulator)