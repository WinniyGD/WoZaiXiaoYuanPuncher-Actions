# -*- encoding:utf-8 -*-
import requests
import json
import os
import utils
from urllib.parse import urlencode
import time
import hashlib
sign_time = int(round(time.time() * 1000)) #13位
content = f"广东省_{t}_广州市"
signature = hashlib.sha256(content.encode('utf-8')).hexdigest()

class WoZaiXiaoYuanPuncher:
    def __init__(self):
        # JWSESSION
        self.jwsession = None
        # 打卡结果
        self.status_code = 0
        # 登陆接口
        self.loginUrl = "https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/username"
        # 请求头
        self.header = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat",
            "Content-Type": "application/json;charset=UTF-8",
            "Content-Length": "2",
            "Host": "gw.wozaixiaoyuan.com",
            "Accept-Language": "en-us,en",
            "Accept": "application/json, text/plain, */*"
        }
        # 请求体（必须有）
        self.body = "{}"

    # 登录
    def login(self):
        username,password = str(os.environ['WZXY_USERNAME']),str(os.environ['WZXY_PASSWORD'])
        url = f'{self.loginUrl}?username={username}&password={password}' 
        self.session = requests.session()
        # 登录
        response = self.session.post(url=url, data=self.body, headers=self.header)
        res = json.loads(response.text)
        if res["code"] == 0:
            print("使用账号信息登录成功")
            jwsession = response.headers['JWSESSION']
            self.setJwsession(jwsession)
            return True
        else:
            print(res)
            print("登录失败，请检查账号信息")
            self.status_code = 5
            return False

    # 设置JWSESSION
    def setJwsession(self, jwsession):
        # 如果找不到cache,新建cache储存目录与文件
        if not os.path.exists('.cache'): 
            print("正在创建cache储存目录与文件...")
            os.mkdir('.cache')
            data = {"jwsession":jwsession}
        elif not os.path.exists('.cache/cache.json'):
            print("正在创建cache文件...")
            data = {"jwsession":jwsession}
        # 如果找到cache,读取cache并更新jwsession
        else:
            print("找到cache文件，正在更新cache中的jwsession...")
            data = utils.processJson('.cache/cache.json').read()
            data['jwsession'] = jwsession                 
        utils.processJson(".cache/cache.json").write(data)
        self.jwsession = data['jwsession']  
    
    # 获取JWSESSION
    def getJwsession(self):
        if not self.jwsession: #读取cache中的配置文件
            data = utils.processJson(".cache/cache.json").read()
            self.jwsession = data['jwsession']  
        return self.jwsession

    # 执行打卡
    def doPunchIn(self):
        print("正在打卡...")
        url = "https://student.wozaixiaoyuan.com/health/save.json"
        self.header['Host'] = "student.wozaixiaoyuan.com"
        self.header['Content-Type'] = "application/x-www-form-urlencoded"
        self.header['JWSESSION'] = self.getJwsession()
        self.header['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat'
        sign_data = {
            "answers": '["0","1","1"]',
            "latitude": os.environ['WZXY_LATITUDE'],
            "longitude": os.environ['WZXY_LONGITUDE'],
            "country": os.environ['WZXY_COUNTRY'],
            "city": os.environ['WZXY_CITY'],
            "district": os.environ['WZXY_DISTRICT'],
            "province": os.environ['WZXY_PROVINCE'],
            "township": os.environ['WZXY_TOWNSHIP'],
            "street": os.environ['WZXY_STREET'],
            "areacode": '440104',
            "towncode": '440104003',
            "citycode": '156440100',
            "timestampHeader": sign_time,
            "signatureHeader": signature,
        }
        print(sign_data)
        data = urlencode(sign_data)
        
        self.session = requests.session()
        response = self.session.post(url=url, data=data, headers=self.header)
        response = json.loads(response.text)
        # 打卡情况        
        # 如果 jwsession 无效，则重新 登录 + 打卡
        if response['code'] == -10:
            print('jwsession 无效，将尝试使用账号信息重新登录')
            self.status_code = 4
            loginStatus = self.login()
            if loginStatus:
                self.doPunchIn()
            else:
                print("重新登录失败，请检查账号信息")
        elif response["code"] == 0:
            self.status_code = 1
            print("打卡成功")
        elif response['code'] == 1:
            self.status_code = 3
            print("打卡失败：今日健康打卡已结束")   
        else:
            print(response)
            print("打卡失败")
                
    # 获取打卡结果
    def getResult(self):
        res = self.status_code
        if res == 1:
            return "✅ 打卡成功"
        elif res == 2:
            return "✅ 你已经打过卡了，无需重复打卡"
        elif res == 3:
            return "❌ 打卡失败，当前不在打卡时间段内"
        elif res == 4:
            return "❌ 打卡失败，jwsession 无效"            
        elif res == 5:
            return "❌ 打卡失败，登录错误，请检查账号信息"
        else:
            return "❌ 打卡失败，发生未知错误，请检查日志"

    # 推送打卡结果
    def sendNotification(self):
        # 如果开启了消息推送
        if os.environ['PUSH_TOKEN']:
            print("正在进行消息推送...")
            url = 'http://www.pushplus.plus/send'
            notifyToken = os.environ['PUSH_TOKEN']
            notifyTime = utils.getCurrentTime()
            notifyResult = self.getResult()
            
            content = json.dumps({
                "打卡项目": "健康打卡",
                "打卡情况": notifyResult,
                "打卡时间": notifyTime
            },ensure_ascii = False)

            msg = {
                "token": notifyToken,
                "title": "⏰ 我在校园打卡结果通知",
                "content": content,
                "template": "json"
            }
            requests.post(url, data = msg)
        else:
            print("未设置PUSH_TOKEN，将不会推送消息")

# 找不到cache，登录+打卡 
wzxy = WoZaiXiaoYuanPuncher()
if not os.path.exists('.cache'): 
    print("找不到cache文件，正在使用账号信息登录...")
    loginStatus = wzxy.login()
    if loginStatus:
        wzxy.doPunchIn()
    else:
        print("登陆失败，请检查账号信息")
else:
    print("找到cache文件，尝试使用jwsession打卡...")
    wzxy.doPunchIn()
wzxy.sendNotification() 
