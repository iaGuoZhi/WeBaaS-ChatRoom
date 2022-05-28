import uuid
import websockets
import requests
import chatroom_pb2
from common.common import *

appName = "python-crud"+str(uuid.uuid4())  # unique app name
appID = None

class Setup():
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

    def __create_schema(self):
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

    def __save_app_id(self):
        with open("common/appid.txt", "w") as f:
            f.write(appID)

    def setup(self):
        self.__register_webaas()
        self.__create_schema()
        self.__save_app_id()


setup = Setup()
setup.setup()
