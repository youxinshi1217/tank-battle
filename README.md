# 坦克大战 · Tank Battle

基于 `pygame` 的 2D 坦克大战游戏。支持单人闯关、双人对战（PVP）、三人对战（PVP3），
包含加速 / 护盾 / 霰弹 / 激光 / 追踪导弹等道具、多张关卡地图（含连续几何碰撞的环岛地图）、
BGM 与音效、底部状态栏三色柔光晕特效。

> 本仓库是**源码发布版**：只含运行必需的源码与素材，不含虚拟环境、打包好的 exe、
> 编译缓存、临时调试脚本和运行时存档。

## 环境要求

- Python **3.10 及以上**（开发环境：Python 3.10.11）
- 唯一第三方依赖：`pygame==2.4.0`

## 快速开始

```bash
# 1. 克隆仓库
git clone <你的仓库地址>
cd tank_battle

# 2. 创建并激活虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行游戏
python main.py
```

Windows 用户装好 Python 与 pygame 后，也可以直接双击 `start_game.bat`。
脚本会依次尝试 `venv_py310`、`.venv`，都没有就用系统 `python`。

如果想让别人不装 Python 也能玩：

```bash
pip install pyinstaller
pyinstaller tank_battle.spec --noconfirm
```

产物在 `dist/tank_battle.exe`。**不要把 `dist/` 提交进仓库**，
请通过 GitHub Releases 上传可执行文件。

## 中文字体（重要）

仓库**不包含任何字体文件**。微软雅黑等系统字体受版权保护，不能随源码分发；
`fonts/` 目录只作为可选的自备字体放置处。

`core/game_fonts.py` 会按以下顺序查找字体，**按已知路径直接加载，不做系统字体枚举**
（枚举注册表在 PyInstaller 打包的 exe 中可能触发 `TypeError` 崩溃）：

1. `fonts/` 下自备的 `msyh.ttc`、`NotoSansCJK-Regular.ttc`、`SourceHanSansSC-Regular.otf`
2. Windows 自带：`C:\Windows\Fonts\msyh.ttc` / `msyhbd.ttc` / `simhei.ttf`
3. macOS 自带：`/System/Library/Fonts/PingFang.ttc`
4. Linux 常见路径：`Noto Sans CJK` / 文泉驿微米黑
   （Debian/Ubuntu：`sudo apt install fonts-noto-cjk`）
5. 以上都没有时退回 pygame 默认字体 —— 此时**中文会显示成方块**，请安装中文字体

Windows 10/11 用户无需任何额外操作，中文界面开箱即用。

## 目录结构

| 路径 | 说明 |
|------|------|
| `main.py` | 游戏入口：主循环、场景切换、结算 |
| `core/` | 配置、碰撞、音频、字体、回合与道具生成 |
| `entities/` | 坦克、子弹、道具、激光、霰弹、追踪导弹 |
| `maps/` | 地图定义、渲染、第五关连续几何碰撞 |
| `stages/` | 关卡流程与关卡背景 |
| `ui/` | 菜单与玩家状态面板 |
| `effects/` | 爆炸、飘分、屏幕震动等特效 |
| `docs/` | 设计文档（仅 markdown，中间预览图未收录） |
| `fonts/` | 可选：自备中文字体（不入库） |
| `save/` | 运行时自动生成的存档（不入库） |
| `_verify_*.py` | 开发期验收脚本，需在项目根目录运行；部分依赖已排除的临时素材，仅供参考 |
| `tank_battle.spec` | PyInstaller 打包配置 |

## 素材说明

- 图片、音乐、音效直接放在仓库根目录，文件名含中文属正常现象，请使用支持 UTF-8 的 Git 客户端克隆。
- 这些素材为项目自用，**仅用于学习与展示**。若要商用或再次公开分发，请先确认每一项素材的授权来源。
- 单个最大文件约 5MB，整份源码压缩包小于 25MB，未超过 GitHub 单文件 100MB 限制，无需 Git LFS。
- 第二关 BGM 原为 24bit/48kHz 无损 FLAC（11.8MB），为控制仓库体积已转码为 320kbps MP3（3.1MB），听感基本一致。

## Git 小提示

中文文件名在 `git status` 里可能被显示成八进制转义，可在仓库内执行：

```bash
git config core.quotepath false
```
