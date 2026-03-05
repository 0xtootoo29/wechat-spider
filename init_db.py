#!/usr/bin/env python3
"""
初始化数据库表
"""
from app.models import init_db

if __name__ == "__main__":
    print("Initializing database tables...")
    init_db()
    print("Database tables created successfully!")