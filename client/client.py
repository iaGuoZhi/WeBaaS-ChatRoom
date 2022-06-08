import threading
import json
import random
import requests
import chatroom_pb2
from datetime import datetime
import asyncio
import websockets
import sys
from cmd import Cmd
from common.common import *

appID = None

class Client(Cmd):
    """
    WeBaaS chatroom client
    """
    prompt = '> '
    intro = '[Welcome] Toy chatroom based on WeBaaS(Cli)\n' + '[Welcome] input help for guidance\n'

    def __init__(self):
        super().__init__()
        self.__id = None
        self.__account = None
        # Toy chatroom only support one channel
        self.__channel_id = 1
        self.__channel = None
        self.__nickname = None
        self.__isLogin = False
        self.__notification_id = None
        self.__setup()

    def __setup(self):
        with open("common/appid.txt", "r") as f:
            global appID
            appID = f.read()

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
        if self.__push_channel(channel):
            self.__isLogin = True

    def __show_members(self):
        self.__pull_channel()
        print("There are {} users in the channel".format(len(self.__channel.accounts)))
        for account in self.__channel.accounts:
            print(account.nickname, end="\t")
        print()

    def __show_msgs(self):
        self.__pull_channel()
        print("There are {} messages in the channel".format(len(self.__channel.messages)))
        for message in self.__channel.messages:
            print("{} {}: {}".format(message.account_name, message.timestamp, message.content), end="\n")
        print()

    def __show_new_in_channel(self, latest_channel):
        # show new members
        for account in latest_channel.accounts:
            if account not in self.__channel.accounts:
                print("Welcome new member : {}".format(account.nickname))

        # show new messages
        for message in latest_channel.messages:
            if message not in self.__channel.messages:
                print("{}\t{}:\t{}".format(message.account_name, message.timestamp, message.content))

    def __pull_channel(self):
        r = requests.get(http_endpoint+"/query",
            params={"appID": appID, "recordKey": self.__channel_id, "schemaName": "chatroom.Channel"})
        if r.status_code != 200:
            print("[Client]: pull channel {} error".format(self.__channel_id))
            return
        channel = chatroom_pb2.Channel()
        channel.ParseFromString(r.content)
        self.__show_new_in_channel(channel)
        self.__channel = channel

    def __listen_channel(self, channel_id):
        # create json
        data_set = {"appID": appID,
                    "recordKeys": [str(self.__channel_id)],
                    "schemaName": "chatroom.Channel"}
        r = requests.post(http_endpoint+"/notification",
            data=json.dumps(data_set))
        if r.status_code != 200:
            print("Error listen channel: "+r.text)
        else:
            self.__notification_id = r.json()["notificationID"]

    def __push_channel(self, channel: chatroom_pb2.Channel):
        # update channel
        r = requests.post(http_endpoint+"/record", params={
            "appID": appID, "schemaName": "chatroom.Channel"},
            data=channel.SerializeToString())
        if r.status_code != 200:
            print("Error updating channel: "+r.text)
            return False
        else:
            self.__channel = channel
            return True

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
        print("Channel {} created.".format(self.__channel_id))

    def __receive_message_thread(self):
        """
        thread for receiving message
        """
        self.__listen_channel(self.__channel_id)

        websocket_url = websocket_endpoint+'/notification?appID={}&notificationID={}'.format(appID, self.__notification_id)
        async def listen_to_websocket():
            async with websockets.connect(websocket_url) as websocket:
                await websocket.recv()
                # only support one channel, to need to extract channel id
                self.__pull_channel()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            asyncio.get_event_loop().run_until_complete(listen_to_websocket())

    def __send_message_thread(self, message_body):
        """
        send message
        :param message_body: message content
        """
        message = chatroom_pb2.Message()
        message.content = message_body
        message.timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        message.account_name = self.__nickname

        self.__pull_channel()
        new_message = self.__channel.messages.add()
        new_message.CopyFrom(message)

        self.__push_channel(self.__channel)

    def __create_account(self, nickname):
        account = chatroom_pb2.Account()
        account.nickname = nickname
        account.id = random.getrandbits(16)
        r = requests.post(http_endpoint+"/record", params={
            "appID": appID, "schemaName": "chatroom.Account"}, data=account.SerializeToString())
        if r.status_code != 200:
            print('[Client]: Error creating account: '+r.text)
            sys.exit(1)

        self.__nickname = account.nickname
        self.__id = account.id
        self.__account = account

    def start(self):
        """
        start client
        """
        self.cmdloop()

    def do_login(self, args):
        """
        login into chatroom
        :param args:  param
        """
        if self.__isLogin:
            print('[Client] already logined.')
            return
        try:
            nickname = args.split(' ')[0]
            identity_key = args.split(' ')[1]

            # Judge identity
            if identity_key != appID[0:3]:
                print('[Client] Wrong identity key')
                return
        except Exception:
            print('[Client] Failed to extract login nickname and identity key')
            return

        self.__create_account(nickname)
        self.__join_channel()

        # Start child thread to receive messages
        thread = threading.Thread(target=self.__receive_message_thread)
        thread.setDaemon(True)
        thread.start()

        print("[Client] Login success!")

    def do_send(self, args):
        """
        Send messages
        :param args: params
        """
        if not self.__isLogin:
            print('[Client] Please login')
            return
        message = args
        # Clear user input line
        print("\033[A                             \033[A")
        # Show this message
        print("me:\t{}".format(message))
        # Start child thread to send messages
        thread = threading.Thread(target=self.__send_message_thread, args=(message,))
        thread.setDaemon(True)
        thread.start()

    def do_logout(self, args=None):
        """
        Logout
        :param args: params
        """
        if not self.__isLogin:
            print('[Client] Please login')
            return
        self.__isLogin = False
        return True

    def do_listuser(self, args=None):
        if not self.__isLogin:
            print('[Client] Please login')
            return
        self.__show_members()

    def do_listmsg(self, args=None):
        if not self.__isLogin:
            print('[Client] Please login')
            return
        self.__show_msgs()

    def do_help(self, arg):
        """
        Help
        :param arg: params
        """
        command = arg.split(' ')[0]
        if command == '':
            print('[Help] login nickname identity - 登录到聊天室，nickname是你选择的昵称，identity是channel的密钥')
            print('[Help] send message - 发送消息，message是你输入的消息')
            print('[Help] listuser - 查看聊天室成员')
            print('[Help] listmsg - 查看所有消息')
            print('[Help] logout - 退出聊天室')
        elif command == 'login':
            print('[Help] login nickname identity - 登录到聊天室，nickname是你选择的昵称，identity是channel的密钥')
        elif command == 'send':
            print('[Help] send message - 发送消息，message是你输入的消息')
        elif command == 'listuser':
            print('[Help] listuser - 查看聊天室成员')
        elif command == 'listmeg':
            print('[Help] listmsg - 查看所有消息')
        elif command == 'logout':
            print('[Help] logout - 退出聊天室')
        else:
            print('[Help] 没有查询到你想要了解的指令')
