"""测试环境：在导入应用之前把数据目录指向临时目录，避免污染 data/。"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ["GAME_DATA_DIR"] = tempfile.mkdtemp(prefix="game-manager-test-")
os.environ.setdefault("GAME_SECRET", "test-secret-do-not-use-in-production")

# 预先建好固定密码的管理员，避免服务启动时生成随机密码
import db  # noqa: E402

db.ensure_admin("admin", "test-pass-123")
