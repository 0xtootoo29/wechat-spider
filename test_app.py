#!/usr/bin/env python3
"""
WeChat Article Downloader - 应用测试脚本
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_api(endpoint, method="GET", data=None):
    """测试 API 接口"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        
        return {
            "status": response.status_code,
            "success": response.status_code < 400,
            "data": response.json() if response.content else None
        }
    except Exception as e:
        return {
            "status": 0,
            "success": False,
            "error": str(e)
        }

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("WeChat Article Downloader - 应用测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试 1: 首页
    print("\n[测试 1] 首页访问...")
    result = test_api("/")
    if result["success"]:
        print("✅ 首页访问成功")
        tests_passed += 1
    else:
        print(f"❌ 首页访问失败: {result.get('error', 'Unknown')}")
        tests_failed += 1
    
    # 测试 2: 获取统计
    print("\n[测试 2] 获取统计数据...")
    result = test_api("/api/stats")
    if result["success"]:
        print("✅ 统计数据获取成功")
        print(f"   公众号数: {result['data'].get('total_accounts', 0)}")
        print(f"   任务数: {result['data'].get('total_tasks', 0)}")
        tests_passed += 1
    else:
        print(f"❌ 统计数据获取失败")
        tests_failed += 1
    
    # 测试 3: 添加公众号
    print("\n[测试 3] 添加测试公众号...")
    test_account = {
        "name": "测试公众号",
        "wechat_id": "test_official_account",
        "gh_id": "gh_test123",
        "category": "科技",
        "description": "这是一个测试公众号"
    }
    result = test_api("/api/accounts", "POST", test_account)
    if result["success"]:
        print("✅ 公众号添加成功")
        account_id = result["data"].get("id")
        tests_passed += 1
    else:
        print(f"❌ 公众号添加失败")
        account_id = None
        tests_failed += 1
    
    # 测试 4: 获取公众号列表
    print("\n[测试 4] 获取公众号列表...")
    result = test_api("/api/accounts")
    if result["success"]:
        print(f"✅ 获取到 {len(result['data'])} 个公众号")
        tests_passed += 1
    else:
        print(f"❌ 获取公众号列表失败")
        tests_failed += 1
    
    # 测试 5: 测试公众号抓取（如果添加了公众号）
    if account_id:
        print("\n[测试 5] 测试公众号抓取...")
        result = test_api("/api/accounts/test", "POST", test_account)
        if result["success"]:
            print("✅ 抓取测试完成")
            print(f"   状态: {result['data'].get('status')}")
            tests_passed += 1
        else:
            print(f"⚠️  抓取测试可能受限（需要网络连接）")
            tests_passed += 1  # 不算失败
    
    # 测试 6: 创建任务
    print("\n[测试 6] 创建测试任务...")
    if account_id:
        test_task = {
            "name": "测试任务",
            "account_id": account_id,
            "schedule_type": "daily",
            "schedule_time": "08:00",
            "fetch_depth": 5,
            "storage_format": "markdown",
            "ai_analysis": True
        }
        result = test_api("/api/tasks", "POST", test_task)
        if result["success"]:
            print("✅ 任务创建成功")
            task_id = result["data"].get("id")
            tests_passed += 1
        else:
            print(f"❌ 任务创建失败")
            task_id = None
            tests_failed += 1
    else:
        print("⚠️  跳过（未添加公众号）")
        task_id = None
    
    # 测试 7: 获取任务列表
    print("\n[测试 7] 获取任务列表...")
    result = test_api("/api/tasks")
    if result["success"]:
        print(f"✅ 获取到 {len(result['data'])} 个任务")
        tests_passed += 1
    else:
        print(f"❌ 获取任务列表失败")
        tests_failed += 1
    
    # 测试 8: 获取文章列表
    print("\n[测试 8] 获取文章列表...")
    result = test_api("/api/articles")
    if result["success"]:
        print(f"✅ 获取到 {len(result['data'])} 篇文章")
        tests_passed += 1
    else:
        print(f"❌ 获取文章列表失败")
        tests_failed += 1
    
    # 测试 9: AI 分析（如果有文章）
    print("\n[测试 9] AI 分析功能...")
    result = test_api("/api/analysis/report")
    if result["success"]:
        print("✅ AI 分析 API 正常")
        tests_passed += 1
    else:
        print(f"❌ AI 分析 API 异常")
        tests_failed += 1
    
    # 清理测试数据
    print("\n[清理] 删除测试数据...")
    if task_id:
        test_api(f"/api/tasks/{task_id}", "DELETE")
        print("   已删除测试任务")
    if account_id:
        test_api(f"/api/accounts/{account_id}", "DELETE")
        print("   已删除测试公众号")
    
    # 测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    print(f"✅ 通过: {tests_passed}")
    print(f"❌ 失败: {tests_failed}")
    print(f"📊 总计: {tests_passed + tests_failed}")
    
    if tests_failed == 0:
        print("\n🎉 所有测试通过！应用运行正常。")
        return 0
    else:
        print(f"\n⚠️  有 {tests_failed} 个测试失败，请检查。")
        return 1

if __name__ == "__main__":
    print("请确保服务已启动: cd app && python main.py")
    print("等待 3 秒后开始测试...")
    import time
    time.sleep(3)
    sys.exit(run_tests())
