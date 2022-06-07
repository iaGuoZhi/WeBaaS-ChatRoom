<div align="center">
    <h1>WeBaaS ChatRoom</h1>
    <h6>一个基于WeBaaS(A simplified MBaaS system)实现的纯命令行聊天室</h6>
</div>

# 预览

![Preview](./doc/preview.gif)

# 环境

* `python` 版本 `3+`
* protoc

# 运行方法

## 注册新应用(可跳过)

由于项目已经向WeBaaS注册过应用，所以这一步骤可以跳过。如果更新了proto文件或者重新开启一个聊天室，则需要执行这个步骤

进入项目根目录，执行命令：

```shell
protoc -I=./proto/ --python_out=./ ./proto/*.proto
```
这一步骤是根据chatroom.proto更新序列化结果


```shell
python3 ./setup.py
```
这一步骤将向WeBaaS注册应用，应用id将存储在文件中

## 运行应用

进入项目根目录，执行命令：

```shell
python3 ./client_start.py
```

来启动聊天室客户端

# 客户端命令

运行之后，你可以在客户端输入命令来使用聊天室功能，输入：

```shell
help
```

可以获取帮助，输入：

```shell
login ${nickname} ${identity}
```

可以以 `${nickname}` 作为用户名登录输入，`${identity}`是appID的前3位，作为聊天室的密钥

```shell
send ${message}
```

可以发送消息 `${message}` 给聊天室登录的所有用户

```shell
listmsg
```

可以查看历史聊天信息

```shell
listmsg
```

可以查看聊天室所有成员
