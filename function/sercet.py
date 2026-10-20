import math
from Crypto.Cipher import AES
import base64
import codecs
import random

def detect_name(text):
    special_chars = '\\/?"*:<>|'  # 注意：反斜杠需要转义
    for char in special_chars:
        if char in text:
            text = text.replace(char, '')
    return text

class Secret_AES:
    def __init__(self):
        self.e = '010001'
        self.f = "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5a" \
                 "a76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46be" \
                 "e255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7"
        self.g = '0CoJUm6Qyw8W8jud'
        self.random_text = self.get_random_str()

    def get_random_str(self):
        str = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        res = ''
        for x in range(16):
            index = math.floor(random.random() * len(str))
            res += str[index]
        return res

    def aes_encrypt(self, text, key):
        iv = '0102030405060708'.encode('utf-8')  # IV 转为 bytes
        key = key.encode('utf-8')                # 密钥转为 bytes
        pad = 16 - len(text.encode()) % 16
        text = text + pad * chr(pad)
        encryptor = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = encryptor.encrypt(text.encode('utf-8'))  # 明文转为 bytes
        return base64.b64encode(ciphertext)

    def rsa_encrypt(self, value, text, modulus):
        '''进行rsa加密'''
        text = text[::-1]
        rs = int(codecs.encode(text.encode('utf-8'), 'hex_codec'), 16) ** int(value, 16) % int(modulus, 16)
        return format(rs, 'x').zfill(256)

    def get_data(self,text):
        params = self.aes_encrypt(text, self.g)
        params = self.aes_encrypt(params.decode('utf-8'), self.random_text)
        enc_sec_key = self.rsa_encrypt(self.e, self.random_text, self.f)
        return {
            'params': params.decode('utf-8'),
            'encSecKey': enc_sec_key
        }