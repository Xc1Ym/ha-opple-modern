# Opple Modern for Home Assistant

这是对 Home Assistant 内置旧版 Opple Wi-Fi 灯集成的现代化重写。它保留原有
`pyoppleio-legacy` 局域网 UDP 协议，同时改用当前 Home Assistant 的 Config Entry、
可视化配置流程、DataUpdateCoordinator、设备注册、诊断与翻译机制。

## 功能

- 在“设置 → 设备与服务 → 添加集成 → Opple”中配置灯名和 IP 地址
- 支持在集成菜单中重新配置 IP 和名称
- 支持开关、0–255 亮度和 3000–5700 K 色温
- 所有阻塞 UDP I/O 都在线程执行器中运行，不阻塞 Home Assistant 事件循环
- 通信失败时实体正确显示为不可用并自动重试
- 为旧版 `light: - platform: opple` YAML 提供一次性自动导入
- 提供诊断数据，并隐藏局域网 IP、MAC 与唯一标识

## 兼容性

- 目标版本：Home Assistant 2026.11 或更新版本
- 设备范围与[官方旧版 Opple 集成](https://www.home-assistant.io/integrations/opple/)一致：
  带 Wi-Fi/手机控制能力的旧款 Opple 灯
- 本集成使用 `opple` 域，会覆盖 Home Assistant 内置的同名旧集成

## 安装

### 手动安装

1. 将 `custom_components/opple` 整个目录复制到 Home Assistant 的
   `/config/custom_components/opple`。
2. 重启 Home Assistant。
3. 在“设置 → 设备与服务 → 添加集成”中搜索 `Opple`。

### HACS 自定义仓库

发布到 GitHub 后，可在 HACS 中将仓库地址作为“集成”类型的自定义仓库添加，
安装后重启 Home Assistant。

## 从旧 YAML 迁移

如果现有配置是：

```yaml
light:
  - platform: opple
    name: keting
    host: 10.10.20.2
  - platform: opple
    name: canting
    host: 10.10.20.3
```

安装本集成并首次重启后，这些条目会自动导入到“设备与服务”。确认两个配置条目
均已出现后，删除上面的 Opple YAML，再重启一次。在线设备会继续使用旧集成生成的
MAC 唯一 ID，因此 Home Assistant 能复用原实体注册表记录；离线设备会保持重试，
待设备恢复在线后完成识别。

也可以完全删除旧 YAML 后，在界面中逐个添加。若灯暂时离线，可打开“允许离线添加”；
该配置条目会处于重试状态，直到设备可访问。

## 为什么不是完全异步依赖

设备协议库 `pyoppleio-legacy` 是同步 UDP 实现。集成本身使用异步 Home Assistant API，
并把库的构造、轮询和控制调用全部放入执行器，同时用锁串行化读写，避免阻塞事件循环
或让轮询与控制命令互相覆盖。

## 开发验证

```bash
python3 -m compileall custom_components
python3 -m unittest discover -s tests
```
