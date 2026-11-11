# -*- coding: utf-8 -*-
"""
地图数据结构
用二维数组 (list[list[TileType]]) 表示整张 25x25 地图。
数组索引方式：grid[row][col]，row 对应 y 方向（从上到下），
col 对应 x 方向（从左到右），与屏幕绘制方向一致。

Phase 5.3 Battle Space Foundation：
  - BATTLE_SPACE_ENABLED=True 时生成确定性战斗空间布局（对称通道 + 四角掩体块）。
  - False 时回退到 Phase 5.2 语义（空地图 + 中央 LJR 拼字装饰）。
尚不包含：随机地图生成算法、多地图切换、可破坏掩体（均后移）。
"""
import core.settings as _settings
from core.settings import GRID_SIZE
from maps.tile import TileType
from maps.letters import LJR_SEQUENCE, LETTER_WIDTH, LETTER_HEIGHT, LETTER_GAP

class GameMap:
    def __init__(self, size: int = GRID_SIZE, data: list = None,
                 is_decorative: list = None):
        self.size = size
        # Phase 8.6+ 连续几何（Stage 5 起）：非 None 时物理碰撞走几何口径，
        # 不再查格子。老关卡恒为 None，行为与以前完全一致。
        self.geometry = None
        # Phase 8.4 装饰覆盖层：(kind, row, col) 列表，纯观感、不参与碰撞/出生。
        self.decorations = None
        if data is not None:
            # Phase 8.0：从外部地图数据加载（由 maps/map_XX.py 提供）。
            # 直接采用传入 grid 与 is_decorative，不再执行默认布局逻辑。
            self.grid = data
            self.is_decorative = (
                is_decorative
                if is_decorative is not None
                else [[False for _ in range(size)] for _ in range(size)]
            )
            return
        # 初始化一张全空地图
        self.grid = [[TileType.EMPTY for _ in range(size)] for _ in range(size)]
        # 标记哪些格子属于 LJR 装饰图案（Phase 5.2 回退模式使用）
        self.is_decorative = [[False for _ in range(size)] for _ in range(size)]
        # 回退开关：运行时读取，False 时复现 Phase 5.2 地图语义
        if _settings.BATTLE_SPACE_ENABLED:
            self._place_battle_space()
        else:
            self._place_ljr_pattern()

    @classmethod
    def from_map_data(cls, data: list, is_decorative: list = None,
                      size: int = GRID_SIZE):
        """从地图数据构建 GameMap（Phase 8.0，供 main.py / LevelManager 使用）。"""
        return cls(size=size, data=data, is_decorative=is_decorative)

    # ------------------------------------------------------------------
    # LJR 拼字
    # ------------------------------------------------------------------
    def _place_ljr_pattern(self) -> None:
        """在地图中央区域用障碍物拼出 LJR 字样。
        三个字母交替使用砖墙 / 钢墙上色，纯粹是为了在可视化阶段
        更容易分辨两种障碍物类型；后续如需统一材质，可以在这里调整。
        """
        letter_tile_types = [TileType.BRICK, TileType.STEEL, TileType.BRICK]
        total_width = (
            LETTER_WIDTH * len(LJR_SEQUENCE)
            + LETTER_GAP * (len(LJR_SEQUENCE) - 1)
        )
        # 计算整体图案在网格中的起始行列，使其居中
        start_col = (self.size - total_width) // 2
        start_row = (self.size - LETTER_HEIGHT) // 2
        cursor_col = start_col
        for letter_pattern, tile_type in zip(LJR_SEQUENCE, letter_tile_types):
            self._stamp_letter(letter_pattern, start_row, cursor_col, tile_type)
            cursor_col += LETTER_WIDTH + LETTER_GAP

    def _stamp_letter(self, pattern, start_row: int, start_col: int, tile_type: TileType) -> None:
        """把单个字母点阵盖到地图指定位置，并标记为装饰图案格子。"""
        for r, row_str in enumerate(pattern):
            for c, ch in enumerate(row_str):
                if ch == "1":
                    grid_row = start_row + r
                    grid_col = start_col + c
                    if 0 <= grid_row < self.size and 0 <= grid_col < self.size:
                        self.grid[grid_row][grid_col] = tile_type
                        self.is_decorative[grid_row][grid_col] = True

    # ------------------------------------------------------------------
    # 战斗空间布局 (Phase 5.3 Battle Space Foundation)
    # ------------------------------------------------------------------
    def _place_battle_space(self) -> None:
        """放置确定性战斗空间布局（中心对称，无随机）。

        规则：
          - 瓦片级碰撞（整格阻挡，视觉随碰撞画满格，见 map_renderer 注释）。
          - 主通道：横向 rows 11-13、纵向 cols 11-13（各 3 格，>= 2 格），保持全空，
            形成"十字主通道"，把地图切成 4 个 11x11 角落区域。
          - 四角区域内放置对称掩体块（不可破坏 BRICK；STEEL 与 BRICK 功能等价，
            本布局统一用 BRICK），以 (r,c)->(r,24-c)->(24-r,c)->(24-r,24-c) 镜像到四角。
          - 左上角 (3,3) 保持空地（玩家出生点，见 main.py spawn_col/row=3,3）。
          - 掩体块均为孤立簇/短段、无闭环 -> 保证全图空地区域连通、无死区。
        """
        # 左上角 11x11 区域（rows 0-10, cols 0-10）的掩体坐标
        tl_walls = [
            (2, 6), (2, 7),
            (4, 2), (4, 3),
            (5, 6),
            (7, 2), (7, 3),
            (8, 7), (8, 8),
            (9, 7), (9, 8), (9, 9),
        ]
        for r, c in tl_walls:
            self._set_battle_wall(r, c)
            self._set_battle_wall(r, 24 - c)
            self._set_battle_wall(24 - r, c)
            self._set_battle_wall(24 - r, 24 - c)

    def _set_battle_wall(self, row: int, col: int) -> None:
        """把格子置为战斗空间障碍（不可破坏 BRICK）。"""
        if 0 <= row < self.size and 0 <= col < self.size:
            self.grid[row][col] = TileType.BRICK

    # ------------------------------------------------------------------
    # 数据访问接口
    # ------------------------------------------------------------------
    def get_tile(self, row: int, col: int) -> TileType:
        return self.grid[row][col]

    def iter_tiles(self):
        """遍历所有非空瓦片，产出 (row, col, tile_type, is_decorative)，
        方便渲染层根据是否为 LJR 装饰图案选择不同的绘制缩放比例。"""
        for row in range(self.size):
            for col in range(self.size):
                tile = self.grid[row][col]
                if tile != TileType.EMPTY:
                    yield row, col, tile, self.is_decorative[row][col]