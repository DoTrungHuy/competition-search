# -*- coding: utf-8 -*-
"""真实浏览器冒烟测试。

为什么需要它：js/app.js 是完全封闭的 IIFE（无任何导出、加载即自动 init），
结构上无法单测，而它承载了列表渲染、搜索、筛选、抽屉与焦点管理。
更重要的是，单测只能证明「函数算得对」，证明不了「算对的结果显示到了屏幕上」——
例如 JS 正确设了 hidden 属性、CSS 的 display 却把它抵消掉，这类跨文件问题
只有真实浏览器能发现。

刻意保持在「冒烟」粒度：只验核心路径，不追求覆盖率。测试要够稳，
否则没人会信它。

依赖 requirements-playwright.txt（项目本就为天池采集器装了 playwright），
另需 `python -m playwright install chromium`。未安装时整体跳过而非失败。
"""
from __future__ import print_function

import functools
import http.server
import os
import socketserver
import sys
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - 环境未装时优雅跳过
    sync_playwright = None


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 静音访问日志，否则测试输出被刷屏


class SiteSmokeTests(unittest.TestCase):
    """整站冒烟：每个用例都从真实 HTTP 加载页面，走完整的 JS 执行路径。"""

    server = None
    thread = None
    playwright = None
    browser = None

    @classmethod
    def setUpClass(cls):
        if sync_playwright is None:
            raise unittest.SkipTest("未安装 playwright，跳过 E2E")

        handler = functools.partial(_QuietHandler, directory=ROOT)
        # 端口 0 交给系统分配，避免与本机开发服务器抢端口
        socketserver.TCPServer.allow_reuse_address = True
        cls.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception as error:  # 内核没下载时给出可操作的提示
            cls.playwright.stop()
            cls.server.shutdown()
            raise unittest.SkipTest(
                "无法启动 chromium（先跑 python -m playwright install chromium）：%s"
                % error
            )

    @classmethod
    def tearDownClass(cls):
        if cls.browser:
            cls.browser.close()
        if cls.playwright:
            cls.playwright.stop()
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()

    def url(self, path="/index.html"):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def open_home(self, **context_kwargs):
        """打开首页并等到列表渲染完成，返回 (context, page)。"""
        context = self.browser.new_context(**context_kwargs)
        page = context.new_page()
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.goto(self.url(), wait_until="networkidle")
        page.wait_for_selector(".card", timeout=10000)
        return context, page

    # 1. 首页能加载赛事数据并渲染
    def test_home_renders_competitions_without_page_errors(self):
        context, page = self.open_home()
        try:
            count = page.locator(".card").count()
            self.assertGreater(count, 0, "首页没有渲染出任何赛事卡片")
            meta = page.locator("#result-meta").inner_text()
            self.assertIn("找到", meta)
            self.assertEqual(self.errors, [], "页面产生了未捕获的 JS 错误")
        finally:
            context.close()

    # 2. 搜索能命中对应赛事
    def test_search_narrows_results_to_matching_competition(self):
        context, page = self.open_home()
        try:
            before = page.locator(".card").count()
            page.fill("#search-input", "蓝桥")
            page.wait_for_function(
                "document.querySelectorAll('.card').length < %d" % before,
                timeout=5000,
            )
            cards = page.locator(".card")
            self.assertGreater(cards.count(), 0, "搜索「蓝桥」应有结果")
            for i in range(cards.count()):
                self.assertIn("蓝桥", cards.nth(i).inner_text())
        finally:
            context.close()

    # 3. 状态芯片筛出的卡片状态必须一致
    def test_open_registration_chip_only_shows_open_competitions(self):
        context, page = self.open_home()
        try:
            page.click(".chip[data-quick='报名中']")
            page.wait_for_timeout(400)
            cards = page.locator(".card")
            if cards.count() == 0:
                self.skipTest("当前数据中没有处于报名中的赛事")
            for i in range(cards.count()):
                text = cards.nth(i).inner_text()
                self.assertRegex(
                    text, r"报名中|即将截止", "「报名中」筛选出了状态不符的卡片"
                )
        finally:
            context.close()

    # 4. 抽屉可开可关，且关闭后焦点回到触发按钮（无障碍要求）
    def test_drawer_opens_and_escape_restores_focus(self):
        context, page = self.open_home()
        try:
            trigger = page.locator(".card button[data-detail]").first
            trigger.click()
            page.wait_for_selector("#drawer.is-open", timeout=5000)
            self.assertEqual(
                page.get_attribute("#drawer", "aria-hidden"),
                "false",
                "抽屉打开后 aria-hidden 应为 false",
            )
            self.assertNotEqual(page.locator("#drawer-title").inner_text().strip(), "")

            page.keyboard.press("Escape")
            page.wait_for_selector("#drawer:not(.is-open)", timeout=5000)
            self.assertEqual(page.get_attribute("#drawer", "aria-hidden"), "true")
            # 焦点必须回到触发它的按钮，否则键盘用户会被丢回页首
            focused = page.evaluate(
                "document.activeElement && document.activeElement.dataset.detail !== undefined"
            )
            self.assertTrue(focused, "Esc 关闭抽屉后焦点未回到「更多信息」按钮")
        finally:
            context.close()

    # 5. 移动端不得横向溢出，触控区不得小于 44px
    def test_mobile_layout_has_no_horizontal_overflow(self):
        context, page = self.open_home(viewport={"width": 375, "height": 812})
        try:
            overflow = page.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1"
            )
            self.assertFalse(overflow, "375px 下页面出现横向滚动")

            small = page.evaluate(
                """() => [...document.querySelectorAll('.topbar a, .topbar button')]
                    .filter(e => e.getBoundingClientRect().height > 0)
                    .filter(e => e.getBoundingClientRect().height < 44)
                    .map(e => e.className)"""
            )
            self.assertEqual(small, [], "顶栏存在小于 44px 的触控目标")
        finally:
            context.close()

    # 6. 深色模式必须能跨刷新保留，且不出现白闪
    def test_dark_theme_persists_across_reload(self):
        context, page = self.open_home()
        try:
            page.click("#theme-toggle")
            page.wait_for_timeout(300)
            theme = page.get_attribute("html", "data-theme")
            self.assertIn(theme, ("dark", "light"))

            page.reload(wait_until="networkidle")
            page.wait_for_selector(".card", timeout=10000)
            self.assertEqual(
                page.get_attribute("html", "data-theme"),
                theme,
                "刷新后主题没有保留",
            )
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
