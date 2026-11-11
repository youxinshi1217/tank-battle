# 字体目录（可选）

本目录**故意不包含任何字体文件**。微软雅黑等系统字体受版权保护，不能随源码上传到 GitHub。

游戏会按已知路径直接加载操作系统自带的中文字体，Windows 10/11、macOS 无需任何操作；
Linux 建议安装 `fonts-noto-cjk`。详见根目录 `README.md` 的「中文字体」一节。

如果你拥有可自由分发的字体（例如 SIL OFL 授权的思源黑体 / Noto Sans CJK），
可以放到这里，游戏会优先使用。支持的文件名：

- `msyh.ttc`
- `NotoSansCJK-Regular.ttc`
- `SourceHanSansSC-Regular.otf`

同时请在 `tank_battle.spec` 的 `datas` 中把该字体加回去，打包 exe 时才会随包携带。
注意：`.gitignore` 默认忽略本目录下所有字体文件，避免误提交。
