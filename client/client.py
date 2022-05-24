import threading
import json
import random
import requests
import uuid
import chatroom_pb2
import datetime
import asyncio
import websockets
import sys
from cmd import Cmd

http_endpoint = "http://202.120.40.82:11232"
websocket_endpoint = "ws://202.120.40.82:11232"
appName = "python-crud"+str(uuid.uuid4())  # unique app name
appID = None

class Client(Cmd):
    """
    客户端
    """
    prompt = ''
    intro = '[Welcome] 简易聊天室客户端(Cli版)\n' + '[Welcome] 输入help来获取帮助\n'

    def __init__(self):
        super().__init__()
        self.__id = None
        self.__account = None
        # Toy chatroom only support one channel
        # self.__channel_id = random.getrandbits(16)
        self.__channel_id = 1
        self.__channel = None
        self.__nickname = None
        self.__isLogin = False
        self.__notification_id = None
        self.__register_webaas()
        self.create_schema()

    def __register_webaas(self):
        global appID
        print("Registering WeBaaS...")
        r = requests.post(http_endpoint+"/app", params={"appName": appName})
        if r.status_code == 200:
            appID = r.json()["appID"]
            print("App registered with ID: "+appID)
        else:
            print("Error registering app: "+r.text)
            sys.exit(1)

    def create_schema(self):
        print("Creating WeBaaS schema...")
        # upload schema file
        with open("proto/chatroom.proto", "rb") as f:
            r = requests.put(http_endpoint+"/schema", data=f.read(), params={
                             "appID": appID, "fileName": "chatroom.proto", "version": "1.0.0"})
            if r.status_code != 200:
                print("Error creating schema: "+r.text)
                sys.exit(1)
            print("[Client]: WeBaaS schema file uploaded.")

        r = requests.post(http_endpoint+"/schema",
                      params={"appID": appID, "version": "1.0.0"})
        if r.status_code != 200:
            print("[Client]: Error updating schema version: "+r.text)
            sys.exit(1)
        print("[Client]: Schema version updated.")

    def __join_channel(self):
        r = requests.get(http_endpoint+"/query",
                         params={"appID": appID, "recordKey": self.__channel_id, "schemaName": "chatroom.Channel"})
        if r.status_code != 200:
            self.__create_channel()
            r = requests.get(http_endpoint+"/query",
                             params={"appID": appID, "schemaName": "chatroom.Channel", "recordKey": self.__channel_id})
            if r.status_code != 200:
                print('[Client]: create channel failed')

        channel = chatroom_pb2.Channel()
        channel.ParseFromString(r.content)
        new_account = channel.accounts.add()
        new_account.CopyFrom(self.__account)
        self.__update_channel(channel)

    def __listen_channel(self, channel_id):
        # create json
        data_set = {"appID": appID,
                    "recordKeys": [str(self.__channel_id)],
                    "schemaName": "chatroom.Channel"}
        r = requests.post(http_endpoint+"/notification",
            data=json.dumps(data_set))
        print(r)
        if r.status_code != 200:
            print("Error listen channel: "+r.text)
        else:
            self.__notification_id = r.json()["notificationID"]
            print("[Client] listen to channel: {}, notificationID: {}".format(self.__channel_id, self.__notification_id))

    def __update_channel(self, channel: chatroom_pb2.Channel):
        # create channel
        r = requests.post(http_endpoint+"/record", params={
            "appID": appID, "schemaName": "chatroom.Channel"},
            data=channel.SerializeToString())
        if r.status_code != 200:
            print("Error updating channel: "+r.text)
        else:
            print("Channel: {} updated.".format(self.__channel_id))

    def __create_channel(self):
        # create channel
        channel = chatroom_pb2.Channel()
        channel.id = self.__channel_id
        r = requests.post(http_endpoint+"/record", params={
            "appID": appID, "schemaName": "chatroom.Channel"},
            data=channel.SerializeToString())
        if r.status_code != 200:
            print("Error creating channel: "+r.text)
            sys.exit(1)
        print("[Client]: Channel {} created.".format(self.__channel_id))

    def __receive_message_thread(self):
        """
        接受消息线程
        """
        self.__listen_channel(self.__channel_id)

        async def listen_to_websocket():
            websocket_url = websocket_endpoint+'/notification?appID={}&notificationID={}'.format(appID, self.__notification_id)
            async with websockets.connect(websocket_url) as websocket:
                r = await websocket.recv()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.get_event_loop().run_until_complete(listen_to_websocket())

    def __send_message_thread(self, message_body):
        """
        发送消息线程
        :param message: 消息内容
        """
        message = chatroom_pb2.Message()
        message.content = message_body
        message.timestamp = datetime.now()
        message.account = self.__account

        new_message = self.__channel.accounts.add()
        new_message.CopyFrom(message)

        self.update_channel(self.__channel)
        print("[Client]: message sent")

    def __create_account(self, nickname):
        account = chatroom_pb2.Account()
        account.nickname = nickname
        account.id = random.getrandbits(16)
        r = requests.post(http_endpoint+"/record", params={
            "appID": appID, "schemaName": "chatroom.Account"}, data=account.SerializeToString())
        if r.status_code != 200:
            print('[Client]: Error creating account: '+r.text)
            sys.exit(1)

        self.__isLogin = True
        self.__nickname = account.nickname
        self.__id = account.id
        self.__account = account
        print('[Client]: Account created, id: {}, nickname: {}'.format(self.__id, self.__nickname))

    def start(self):
        """
        启动客户端
        """
        self.cmdloop()

    def do_login(self, args):
        """
        登录聊天室
        :param args: 参数
        """
        try:
            nickname = args.split(' ')[0]
            identity_key = args.split(' ')[1]

            # Judge identity
            if identity_key not in appID:
                print('[Client] Wrong identity key')
                return
        except Exception:
            print('[Client] Failed to extract login nickname and identity key')
            return

        self.__create_account(nickname)
        self.__join_channel()

        # 开启子线程用于接受数据
        thread = threading.Thread(target=self.__receive_message_thread)
        thread.setDaemon(True)
        thread.start()

    def do_send(self, args):
        """
        发送消息
        :param args: 参数
        """
        message = args
        # 显示自己发送的消息
        print('[' + str(self.__nickname) + '(' + str(self.__id) + ')' + ']', message)
        # 开启子线程用于发送数据
        thread = threading.Thread(target=self.__send_message_thread, args=(message,))
        thread.setDaemon(True)
        thread.start()

    def do_logout(self, args=None):
        """
        登出
        :param args: 参数
        """
        self.__isLogin = False
        return True

    def do_help(self, arg):
        """
        帮助
        :param arg: 参数
        """
        command = arg.split(' ')[0]
        if command == '':
            print('[Help] login nickname - 登录到聊天室，nickname是你选择的昵称')
            print('[Help] send message - 发送消息，message是你输入的消息')
            print('[Help] logout - 退出聊天室')
        elif command == 'login':
            print('[Help] login nickname - 登录到聊天室，nickname是你选择的昵称')
        elif command == 'send':
            print('[Help] send message - 发送消息，message是你输入的消息')
        elif command == 'logout':
            print('[Help] logout - 退出聊天室')
        else:
            print('[Help] 没有查询到你想要了解的指令')
