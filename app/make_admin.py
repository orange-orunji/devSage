# -*- coding: utf-8 -*-
"""把指定用户提升为管理员：python -m app.make_admin <用户名> [--revoke]"""
import sys

from app.utils.SQL_database import SessionLocal
from app.schemas.user import User


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python -m app.make_admin <用户名> [--revoke]")
        return 1
    username = sys.argv[1]
    revoke = "--revoke" in sys.argv[2:]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"用户不存在: {username}")
            return 2
        user.role = "user" if revoke else "admin"
        db.commit()
        print(f"{username} 角色已设为 {user.role}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
