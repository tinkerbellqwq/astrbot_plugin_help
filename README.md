
<div align="center">

![:astrbot_plugin_help](https://count.getloli.com/@:astrbot_plugin_help?theme=minecraft)

# 更好的帮助

_✨ [astrbot](https://github.com/AstrBotDevs/AstrBot) 帮助插件 ✨_  

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/AstrBot-3.4%2B-orange.svg)](https://github.com/Soulter/AstrBot)
[![GitHub](https://img.shields.io/badge/作者-Zhalslar-blue)](https://github.com/Zhalslar)

</div>

# astrbot_plugin_help

## ⚠️⚠️⚠️ 旧版更新请注意 ⚠️⚠️⚠️
- 尽可能卸载后重新从插件市场安装本插件（卸载旧版时请勾选 `同时删除插件配置文件`）

## 🤝 介绍

查看所有命令，包括插件，返回一张帮助图片

## 📦 安装

- 可以直接在astrbot的插件市场搜索astrbot_plugin_help，点击安装，耐心等待安装完成即可
- 若是安装失败，可以尝试直接克隆源码：

```bash
# 克隆仓库到插件目录
cd /AstrBot/data/plugins
git clone https://github.com/Zhalslar/astrbot_plugin_help

# 控制台重启AstrBot
```

## 🐔 使用说明

### 命令表

|  命令    |     说明     |
|:--------:|:--------------|
| `/helps` | 生成帮助图, 别名：`帮助``菜单``功能` |

### 示例图

![7791647af2717a4a933d209a4a1cd722_720](https://github.com/user-attachments/assets/cb29069c-5692-4b02-9747-0efb095c3c0d)

### 繁体字/生僻字显示

插件自带字体(抖音美好体)只覆盖简体常用字。生成图片时若遇到缺失字形(如繁体字`豬``強`),会自动改用回退字体补齐渲染,回退字体的查找顺序为:

1. 插件配置 `font_path_fallback` 中指定的字体文件路径
2. 插件目录下 `fonts/` 文件夹内的字体文件(.ttf/.otf/.ttc)
3. 系统常见中文字体(微软雅黑 / PingFang / Noto Sans CJK / 文泉驿等)

插件已在 `fonts/` 目录内置了繁体回退字体 `FallbackTC-Regular.otf`(基于 Noto Sans TC 子集化,约 3MB,SIL OFL 1.1 许可),开箱即可正确显示繁体字,无需额外配置。如需替换回退字体,可自行放入 `fonts/` 目录或在插件配置中填写字体路径。

# 支持

本插件改自Astrbot默认插件。
[帮助文档](https://astrbot.app)
