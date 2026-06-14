import sys, os
sys.path.insert(0, r'E:\工作学习\Code项目\SunwodaTool\Lenovo Tools\LenovoTool2_V1.0\src')

# Monkey-patch _ask_demo_fallback to always return True
import lenovo_tool.main as _main
_orig = _main._ask_demo_fallback
_main._ask_demo_fallback = lambda *a, **kw: True

sys.exit(_main.main())
