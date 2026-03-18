# -*- coding: utf-8 -*-
"""
工具模块 - 日志 (utils/logger.py)
统一日志配置：同时输出到控制台和滚动文件。
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_initialized: set = set()


def get_logger(name: str = "yuan_quant") -> logging.Logger:
    """
    获取已配置好的 Logger 实例（单例模式，避免重复添加 Handler）。

    Parameters
    ----------
    name : str  Logger 名称，建议传入 __name__

    Returns
    -------
    logging.Logger
    """
    # 延迟导入，避免循环依赖
    from config.settings import LOGGING

    logger = logging.getLogger(name)

    if name in _initialized:
        return logger

    level = getattr(logging, LOGGING["level"].upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 Handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 文件 Handler（滚动日志）
    log_dir = LOGGING["log_dir"]
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, LOGGING["log_file"])
    fh = RotatingFileHandler(
        log_path,
        maxBytes=LOGGING["max_bytes"],
        backupCount=LOGGING["backup_count"],
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    _initialized.add(name)
    return logger


if __name__ == "__main__":
    print("=== Logger 模块测试 ===")

    log = get_logger("test_logger")
    log.debug("这是一条 DEBUG 日志（默认 INFO 级别下不显示）")
    log.info("这是一条 INFO 日志")
    log.warning("这是一条 WARNING 日志")
    log.error("这是一条 ERROR 日志")

    # 验证单例：重复获取同名 logger 不会重复添加 Handler
    log2 = get_logger("test_logger")
    assert log is log2, "单例测试失败：两次获取的 logger 不是同一个对象"
    print(f"[单例测试] 通过，Handler 数量: {len(log.handlers)}")

    # 获取另一个模块级 logger
    log3 = get_logger("another_module")
    log3.info("来自另一个模块的日志")

    print("=== 测试完成，日志文件已写入 logs/ 目录 ===")
