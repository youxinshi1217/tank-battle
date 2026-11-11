# -*- coding: utf-8 -*-
"""独立模拟：复现 _resolve_collision 的坦克互撞核心逻辑，断言帧末不重叠。
不依赖 pygame / 显示，仅验证"一碰就退回原位"能否维持不重叠不变式。
"""
import random

TANK = 25.6          # 与 settings.TANK_SIZE 一致 (TILE_SIZE*0.8, TILE_SIZE=32)
HALF = TANK / 2.0
SW, SH = 800, 800    # 屏幕边界
MAX_STEP = 2.5       # 每帧最大位移 ≈ TANK_SPEED(150)/60，远小于 TANK

class Tank:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.rect = self._mk()

    def _mk(self):
        return (self.x - HALF, self.y - HALF, TANK, TANK)  # (left, top, w, h)

    def sync_rect(self):
        self.rect = self._mk()


def overlap(a, b):
    # a,b = (left, top, w, h)
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]
                or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def resolve(tank, others, old_x, old_y):
    # 屏幕边界约束（与真实代码一致）
    tank.x = clamp(tank.x, HALF, SW - HALF)
    tank.y = clamp(tank.y, HALF, SH - HALF)
    tank.sync_rect()  # 必须先同步候选位置再判重叠
    for o in others:
        if o is tank:
            continue
        if overlap(tank.rect, o.rect):
            tank.x, tank.y = old_x, old_y
            tank.sync_rect()
            break


def run(seed, scenario):
    random.seed(seed)
    if scenario == "headon":
        p1, p2 = Tank(300, 400), Tank(500, 400)   # 面对面
    else:
        p1, p2 = Tank(150, 150), Tank(650, 650)
    frames = 4000
    for f in range(frames):
        # P1：随机移动（含朝 P2 方向的分量）
        p1_old = (p1.x, p1.y)
        if scenario == "headon":
            dx1 = 1.0 if p2.x > p1.x else -1.0
            dy1 = 0.0
        else:
            dx1 = random.uniform(-1, 1)
            dy1 = random.uniform(-1, 1)
        p1.x += dx1 * MAX_STEP
        p1.y += dy1 * MAX_STEP
        resolve(p1, [p2], *p1_old)

        # P2：随机移动（headon 时朝 P1 压）
        p2_old = (p2.x, p2.y)
        if scenario == "headon":
            dx2 = -1.0 if p1.x > p2.x else 1.0
            dy2 = 0.0
        else:
            dx2 = random.uniform(-1, 1)
            dy2 = random.uniform(-1, 1)
        p2.x += dx2 * MAX_STEP
        p2.y += dy2 * MAX_STEP
        resolve(p2, [p1], *p2_old)

        # 帧末断言：两坦克矩形绝不重叠
        if overlap(p1.rect, p2.rect):
            return False, f"seed={seed} scenario={scenario} frame={f} overlap p1={p1.rect} p2={p2.rect}"
    return True, f"seed={seed} scenario={scenario} OK after {frames} frames"


if __name__ == "__main__":
    results = []
    for s in range(20):
        results.append(run(s, "headon"))
        results.append(run(s, "random"))
    failed = [r for ok, r in results if not ok]
    for ok, r in results:
        print(("PASS" if ok else "FAIL"), r)
    print("\n=== SUMMARY:", "ALL PASS" if not failed else f"{len(failed)} FAILED ===")
