# MaiBot-Milky-Adapter

MaiBot 的 [Milky 协议](https://github.com/SaltifyDev/milky) 适配器插件，用于连接支持 Milky 协议的 QQ 协议端（如 LagrangeV2、Acidify 等）。

## 简介

MaiBot-Milky-Adapter 是一个第三方 MaiBot 插件，承担 QQ 平台消息网关职责：

- 通过 HTTP API 调用 Milky 协议端接口
- 通过 SSE 或 WebSocket 接收 Milky 协议端推送的事件
- 将入站消息与通知事件转换为 MaiBot Host 侧标准结构
- 将 Host 出站消息转换为 Milky API 调用并发送

## 与 NapCat 适配器的区别

| 特性 | MaiBot-Napcat-Adapter | MaiBot-Milky-Adapter |
|------|----------------------|---------------------|
| 协议 | OneBot v11 | Milky |
| API 调用方式 | WebSocket action/params/echo | HTTP POST `/api/:api` |
| 事件接收方式 | WebSocket 双工 | SSE `/event` 或 WebSocket `/event` |
| 连接模式 | 正向 WebSocket 客户端 | HTTP 客户端 |

## 前置要求

- [MaiBot](https://github.com/Mai-with-u/MaiBot) >= 1.0.0 (pre.24+)
- [MaiBot SDK](https://github.com/Mai-with-u) >= 2.0.0
- Python >= 3.10
- 支持 Milky 协议的协议端（如 [LagrangeV2](https://github.com/LagrangeDev/LagrangeV2)、[Acidify](https://github.com/LagrangeDev/acidify) 等）
- `aiohttp` 库（用于 HTTP 通信）

## 安装

将本项目作为 MaiBot 插件放置到插件目录即可。

## 配置

配置通过 **MaiBot 主程序** 管理：

在 MaiBot 主程序的 WebUI 管理界面中找到 `Milky Adapter`，直接在界面中填写配置即可。

首次使用时，至少需要在 `milky_server` 中配置正确的 `host` 和 `port`，并将 `plugin.enabled` 设为 `true`。

### 配置说明

#### milky_server

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | string | `127.0.0.1` | Milky 协议端主机地址 |
| `port` | int | `3000` | Milky 协议端 HTTP 服务端口 |
| `token` | string | `""` | 访问令牌，协议端未启用鉴权时留空 |
| `event_mode` | string | `websocket` | 事件接收模式，可选 `websocket` 或 `sse` |
| `reconnect_delay_sec` | float | `5.0` | 连接断开后的重连等待秒数 |
| `action_timeout_sec` | float | `15.0` | API 调用超时秒数 |
| `connection_id` | string | `""` | 可选连接标识，用于多链路场景 |

#### chat

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_chat_list_filter` | bool | `true` | 是否启用聊天名单过滤 |
| `group_list_type` | string | `whitelist` | 群聊名单模式 |
| `group_list` | list | `[]` | 群聊名单群号列表 |
| `private_list_type` | string | `whitelist` | 私聊名单模式 |
| `private_list` | list | `[]` | 私聊名单用户 ID 列表 |
| `ban_user_id` | list | `[]` | 全局屏蔽用户 ID 列表 |

#### filters

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ignore_self_message` | bool | `true` | 是否忽略机器人自身消息 |
| `regex_filter_enabled` | bool | `false` | 是否启用正则过滤 |
| `regex_filter_mode` | string | `blacklist` | 正则过滤模式 |
| `regex_filter_patterns` | list | `[]` | 正则表达式列表 |

## 公开 API

适配器注册了以下 MaiBot 公开 API：

### 账号相关

| API 名称 | 说明 |
|----------|------|
| `adapter.milky.account.get_login_info` | 获取登录信息 |
| `adapter.milky.account.get_stranger_info` | 获取用户信息 |
| `adapter.milky.account.get_friend_list` | 获取好友列表 |
| `adapter.milky.account.set_nickname` | 设置昵称 |
| `adapter.milky.account.set_bio` | 设置个性签名 |
| `adapter.milky.account.send_poke` | 发送戳一戳 |
| `adapter.milky.account.send_friend_nudge` | 发送好友戳一戳 |

### 群组相关

| API 名称 | 说明 |
|----------|------|
| `adapter.milky.group.get_group_info` | 获取群信息 |
| `adapter.milky.group.get_group_list` | 获取群列表 |
| `adapter.milky.group.get_group_member_info` | 获取群成员信息 |
| `adapter.milky.group.get_group_member_list` | 获取群成员列表 |
| `adapter.milky.group.set_group_name` | 设置群名称 |
| `adapter.milky.group.set_group_member_card` | 设置群名片 |
| `adapter.milky.group.set_group_member_mute` | 设置群成员禁言 |
| `adapter.milky.group.set_group_whole_mute` | 设置群全体禁言 |
| `adapter.milky.group.kick_group_member` | 踢出群成员 |
| `adapter.milky.group.send_group_nudge` | 发送群戳一戳 |
| `adapter.milky.group.recall_group_message` | 撤回群消息 |
| `adapter.milky.group.quit_group` | 退出群 |

### 消息相关

| API 名称 | 说明 |
|----------|------|
| `adapter.milky.message.recall_private_message` | 撤回私聊消息 |
| `adapter.milky.message.get_resource_temp_url` | 获取资源临时链接 |
| `adapter.milky.message.mark_message_as_read` | 标记消息已读 |

### 文件相关

| API 名称 | 说明 |
|----------|------|
| `adapter.milky.file.upload_private_file` | 上传私聊文件 |
| `adapter.milky.file.upload_group_file` | 上传群文件 |

### 系统相关

| API 名称 | 说明 |
|----------|------|
| `adapter.milky.system.get_impl_info` | 获取协议端信息 |
| `adapter.milky.system.get_user_profile` | 获取用户个人信息 |
| `adapter.milky.system.set_avatar` | 设置头像 |

### 通用

| API 名称 | 说明 |
|----------|------|
| `adapter.milky.action.call` | 调用任意 Milky API |
| `adapter.milky.action.call_data` | 调用任意 Milky API 并返回 data 字段 |

## 支持的事件

适配器支持以下 Milky 事件的接收和转换：

### 消息事件
- `message_receive` - 消息接收（支持 friend、group、temp 场景）

### 通知事件
- `message_recall` - 消息撤回
- `friend_request` - 好友请求
- `group_join_request` - 入群请求
- `group_invited_join_request` - 邀请入群请求
- `group_invitation` - 入群邀请
- `friend_nudge` - 好友戳一戳
- `group_nudge` - 群戳一戳
- `group_member_increase` - 群成员增加
- `group_member_decrease` - 群成员减少
- `group_mute` - 群禁言
- `group_whole_mute` - 群全体禁言
- `group_admin_change` - 群管理员变更
- `group_name_change` - 群名称变更
- `group_message_reaction` - 群消息表情回应
- `group_essence_message_change` - 群精华消息变更
- `bot_offline` - 机器人离线

## 消息段支持

### 入站消息段（Milky → MaiBot）

| Milky 段类型 | Host 段类型 | 说明 |
|-------------|------------|------|
| `text` | `text` | 文本 |
| `mention` | `at` | @某人 |
| `mention_all` | `at` | @全体 |
| `face` | `text` | QQ 表情（降级为文本） |
| `reply` | `reply` | 回复 |
| `image` | `image` / `emoji` | 图片 / 表情 |
| `record` | `voice` | 语音 |
| `video` | `video` | 视频 |
| `file` | `text` | 文件（降级为文本） |
| `forward` | `forward` | 合并转发 |
| `market_face` | `emoji` / `text` | 商城表情 |

### 出站消息段（MaiBot → Milky）

| Host 段类型 | Milky 段类型 | 说明 |
|------------|-------------|------|
| `text` | `text` | 文本 |
| `at` | `mention` / `mention_all` | @某人 / @全体 |
| `reply` | `reply` | 回复 |
| `image` | `image` | 图片 |
| `emoji` | `image` (sticker) | 表情 |
| `voice` | `record` | 语音 |
| `video` | `video` | 视频 |
| `file` | `file` | 文件 |
| `forward` | `forward` | 合并转发 |

## 项目结构

```
MaiBot-Milky-Adapter/
├── __init__.py              # 包入口
├── _manifest.json           # 插件清单
├── plugin.py                # 主插件类
├── config.py                # 配置模型
├── constants.py             # 常量定义
├── types.py                 # 类型定义
├── transport.py             # 传输层
├── filters.py               # 消息过滤
├── heartbeat_monitor.py     # 连接状态监测
├── runtime_state.py         # 网关状态上报
├── apis/                    # API 端点
├── codecs/                  # 编解码器
│   ├── inbound/             # 入站消息编解码
│   ├── outbound/            # 出站消息编解码
│   └── notice/              # 通知事件编解码
├── runtime/                 # 运行时组件
│   ├── builder.py           # 组件构建器
│   ├── bundle.py            # 组件容器
│   └── router.py            # 事件路由器
└── services/                # 服务层
    ├── action_service.py    # 底层动作调用
    └── query_service.py     # 查询服务
```

## 参考项目

- [MaiBot-Napcat-Adapter](https://github.com/Mai-with-u/MaiBot-Napcat-Adapter) - NapCat 适配器实现参考
- [Milky](https://github.com/SaltifyDev/milky) - Milky 协议规范
- [maim_message](https://github.com/Mai-with-u/maim_message) - MaiBot 消息接口库

## 许可证

GPL-v3.0-or-later

---

> 本项目由 vibe_coding 完成，如有问题请提交 [Issue](https://github.com/LuoRogers/MaiBot-Milky-Adapter/issues)。
