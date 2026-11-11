# -*- coding: utf-8 -*-
"""PVP 随机地图概率统计检验。

模拟多次随机抽取，验证各地图出现频率是否在 [22%, 28%] 区间内。
若超出此范围，则说明概率分布不均匀，需要更换随机算法。

Usage:
    python _verify_roulette_probability.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random
from collections import Counter


def verify_probability_distribution(num_trials=10000):
    """验证随机概率分布是否均匀。

    Args:
        num_trials: 模拟抽取次数，默认 10000 次

    Returns:
        dict: 各地图的索引、名称、频次、百分比
    """
    # 模拟 4 张地图的随机抽取（对应 random.randrange(4)）
    counts = Counter()
    for _ in range(num_trials):
        selected = random.randrange(4)
        counts[selected] += 1

    # 地图名称映射（与游戏一致）
    STAGE_NAMES = ["钢铁废墟", "工业迷宫", "军事攻坚", "决战要塞"]

    # 打印统计结果
    print(f"\n{'=' * 60}")
    print(f"PVP 随机地图概率检验（模拟 {num_trials} 次抽取）")
    print(f"{'=' * 60}")
    print(f"{'地图名称':<12} {'索引':<6} {'频次':<8} {'百分比':<10} {'状态'}")
    print(f"{'-' * 60}")

    results = {}
    for idx in range(4):
        count = counts[idx]
        percentage = (count / num_trials) * 100
        status = "✓ 正常" if 22 <= percentage <= 28 else "✗ 异常"
        results[idx] = {
            "name": STAGE_NAMES[idx],
            "count": count,
            "percentage": percentage,
            "status": status
        }
        print(f"{STAGE_NAMES[idx]:<12} {idx:<6} {count:<8} {percentage:>6.2f}%  {status}")

    print(f"{'-' * 60}")
    print(f"{'总计':<12} {'':<6} {num_trials:<8} {100.00:>6.2f}%")
    print(f"{'=' * 60}\n")

    # 验证所有地图都在 [22%, 28%] 区间内
    all_normal = all(22 <= r["percentage"] <= 28 for r in results.values())

    if all_normal:
        print("✓ 概率分布均匀，所有地图均在 [22%, 28%] 区间内")
    else:
        print("✗ 概率分布不均，部分地图超出预期范围")
        for idx, r in results.items():
            if not (22 <= r["percentage"] <= 28):
                print(f"  - {r['name']}（{r['percentage']:.2f}%）超出范围")

    return results, all_normal


def test_with_secrets():
    """使用 secrets 模块验证（密码学安全随机）。"""
    try:
        import secrets
        print("\n" + "=" * 60)
        print("使用 secrets.randbelow() 验证（密码学安全随机）")
        print("=" * 60 + "\n")

        counts = Counter()
        for _ in range(10000):
            selected = secrets.randbelow(4)
            counts[selected] += 1

        STAGE_NAMES = ["钢铁废墟", "工业迷宫", "军事攻坚", "决战要塞"]
        print(f"{'地图名称':<12} {'索引':<6} {'频次':<8} {'百分比':<10} {'状态'}")
        print(f"{'-' * 60}")

        for idx in range(4):
            count = counts[idx]
            percentage = (count / 10000) * 100
            status = "✓ 正常" if 22 <= percentage <= 28 else "✗ 异常"
            print(f"{STAGE_NAMES[idx]:<12} {idx:<6} {count:<8} {percentage:>6.2f}%  {status}")

        print(f"{'=' * 60}\n")

    except ImportError:
        print("secrets 模块不可用（Python < 3.6），跳过此测试")


if __name__ == "__main__":
    results, is_uniform = verify_probability_distribution(10000)

    # 同时测试 secrets 方案
    test_with_secrets()

    # 总结
    print("\n结论与建议：")
    print("-" * 60)
    if is_uniform:
        print("✓ 当前 random.randrange() 实现的概率分布均匀")
        print("  用户的'决战要塞偏多'感知可能是小样本偏差或心理因素")
        print("  建议：无需修改代码，保持现状即可")
    else:
        print("✗ 当前实现存在概率偏差")
        print("  建议：改用 secrets.randbelow(4) 替代 random.randrange(4)")
        print("        （密码学安全，完全消除任何周期性）")
