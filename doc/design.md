<div align="center">
    <h1>WeBaaS ChatRoom</h1>
    <h6>一个基于WeBaaS(A simplified MBaaS system)实现的纯命令行聊天室</h6>
</div>

# 预览

![Preview](./preview.png)

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

### 客户端命令

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

# 系统架构

## 数据库设计

![](../slides/image/proto_structure.png)

数据库包括三个表: Accounts, Message, Channel.

Channel包括这个频道里面的所有用户和聊天内容。

Message包括消息内容，消息时间戳，消息发送者。

Accounts包括用户id和昵称。

## 多线程

发送消息会开启一个子线程来发送消息。

用户在登录之后就会有一个子线程通过websocket监听WeBaaS的notification。

## 与WeBaaS交互

使用了WeBaaS的6个接口，包括app, schema, query, record, notification register, and notification listen.

以发送与接收消息为例
当用户发送一条消息的时候，我们将用户的消息添加到Channel中，并通过record接口发送给WeBaaS。这个channel中的其他用户的客户端由于正在监听这个channel，它们会收到channel被更新的通知，并通过query请求从WeBaaS中拿到channel中的最新内容。从最新的channel中找到新的消息，并展示给用户。

## 与用户交互

用户能够通过login命令登录，通过send命令发送消息，通过listmsg查看历史消息，通过listuser查看所有用户，通过logout登出。
