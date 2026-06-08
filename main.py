#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
古建筑木构件测绘数据管理系统
入口文件
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import main

if __name__ == "__main__":
    main()
