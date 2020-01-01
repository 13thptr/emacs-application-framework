#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2018 Andy Stewart
#
# Author:     Andy Stewart <lazycat.manatee@gmail.com>
# Maintainer: Andy Stewart <lazycat.manatee@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QColor, QPainter, QFont, QTextDocument
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QWidget, QApplication, QWidget, QListWidget, QVBoxLayout, QLabel, QPushButton, QListWidgetItem, QStackedWidget, QSizePolicy
from core.buffer import Buffer
from PyQt5 import QtWidgets, QtCore
from core.browser import BrowserView
import feedparser
import os

class AppBuffer(Buffer):
    def __init__(self, buffer_id, url, arguments):
        Buffer.__init__(self, buffer_id, url, arguments, True, QColor(0, 0, 0, 255))

        self.add_widget(RSSReaderWidget())

    def handle_input_message(self, result_type, result_content):
        if result_type == "add_subscription":
            self.buffer_widget.add_subscription(result_content)

    def add_subscription(self):
        self.buffer_widget.send_input_message("Subscribe to RSS feed: ", "add_subscription")

class RSSReaderWidget(QWidget):

    def __init__(self):
        super(RSSReaderWidget, self).__init__()

        self.feed_file_path = os.path.expanduser("~/.emacs.d/eaf/rss-reader/feeds.txt")

        self.feed_area = QWidget()
        self.feed_list = QListWidget()
        self.feed_list.setStyleSheet( """QListWidget{background: #4D5250;}""")
        panel_layout = QVBoxLayout()
        panel_layout.setSpacing(0)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self.feed_list)
        self.feed_area.setLayout(panel_layout)

        self.article_area = QWidget()
        self.article_list = QListWidget()
        self.article_list.verticalScrollBar().setStyleSheet("QScrollBar {width:0px;}");
        article_layout = QVBoxLayout()
        article_layout.setSpacing(0)
        article_layout.setContentsMargins(0, 0, 0, 0)

        self.browser = BrowserView()

        article_layout.addWidget(self.article_list)
        article_layout.addWidget(self.browser)

        article_layout.setStretchFactor(self.article_list, 1)
        article_layout.setStretchFactor(self.browser, 3)

        self.article_area.setLayout(article_layout)

        self.welcome_page = QWidget()
        self.welcome_page_box = QVBoxLayout()
        self.welcome_page_box.setSpacing(10)
        self.welcome_page_box.setContentsMargins(0, 0, 0, 0)

        welcome_title_label = QLabel("Welcome to EAF RSS Reader!")
        welcome_title_label.setFont(QFont('Arial', 24))
        welcome_title_label.setStyleSheet("QLabel {color: black; font-weight: bold; margin: 20px;}")
        welcome_title_label.setAlignment(Qt.AlignHCenter)

        add_subscription_label = QLabel("Press key 'a' to add subscription")
        add_subscription_label.setFont(QFont('Arial', 20))
        add_subscription_label.setStyleSheet("QLabel {color: #333;}")
        add_subscription_label.setAlignment(Qt.AlignHCenter)

        self.welcome_page_box.addStretch(1)
        self.welcome_page_box.addWidget(welcome_title_label)
        self.welcome_page_box.addWidget(add_subscription_label)
        self.welcome_page_box.addStretch(1)

        self.welcome_page.setLayout(self.welcome_page_box)

        self.right_area = QStackedWidget()
        self.right_area.addWidget(self.welcome_page)
        self.right_area.addWidget(self.article_area)

        self.right_area.setCurrentIndex(0)

        hbox = QHBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)

        hbox.addWidget(self.feed_area)
        hbox.addWidget(self.right_area)

        hbox.setStretchFactor(self.feed_area, 1)
        hbox.setStretchFactor(self.right_area, 3)

        self.setLayout(hbox)

        self.article_list.itemActivated.connect(self.handle_article)

    def handle_article(self, article_item):
        self.browser.setUrl(QUrl(article_item.post_link))

    def add_subscription(self, feed_link):
        # https://sachachua.com/blog/feed/

        self.fetchThread = FetchRSSThread(feed_link)
        self.fetchThread.fetch_rss.connect(self.handle_rss)
        self.fetchThread.invalid_rss.connect(self.handle_invalid_rss)
        self.fetchThread.start()

    def save_feed(self, feed_link):
        if not os.path.exists(self.feed_file_path):
            basedir = os.path.dirname(self.feed_file_path)
            if not os.path.exists(basedir):
                os.makedirs(basedir)

            with open(self.feed_file_path, "a"):
                os.utime(self.feed_file_path, None)

        with open(self.feed_file_path, "r") as feed_file:
            lines = map(lambda x: x.strip(), feed_file.readlines())
            if feed_link not in lines:
                with open(self.feed_file_path, "w") as f:
                    f.write(feed_link + "\n")
                self.message_to_emacs.emit("Add feed: " + feed_link)

    def handle_rss(self, feed_object, feed_link, feed_title):
        self.save_feed(feed_link)

        self.right_area.setCurrentIndex(1)

        feed_item = QListWidgetItem(self.feed_list)
        feed_item_widget = RSSFeedItem(feed_object, len(feed_object.entries))
        feed_item.setSizeHint(feed_item_widget.sizeHint())
        self.feed_list.addItem(feed_item)
        self.feed_list.setItemWidget(feed_item, feed_item_widget)

        self.browser.setUrl(QUrl(feed_object.entries[0].link))

        for post in feed_object.entries:
            item_widget = RSSArticleItem(post)
            item = QListWidgetItem(self.article_list)
            item.post_link = item_widget.post_link
            item.setSizeHint(item_widget.sizeHint())
            self.article_list.addItem(item)
            self.article_list.setItemWidget(item, item_widget)

    def handle_invalid_rss(self, feed_link):
        self.message_to_emacs.emit("Invalid feed link: " + feed_link)

class FetchRSSThread(QtCore.QThread):
    fetch_rss = QtCore.pyqtSignal(object, str, str)
    invalid_rss = QtCore.pyqtSignal(str)

    def __init__(self, feed_link):
        super().__init__()
        self.feed_link = feed_link

    def run(self):
        try:
            d = feedparser.parse(self.feed_link)
            self.fetch_rss.emit(d, self.feed_link, d.feed.title)
        except Exception:
            import traceback
            traceback.print_exc()

            self.invalid_rss.emit(self.feed_link)

class RSSFeedItem(QWidget):

    def __init__(self, feed_object, post_num):
        super(RSSFeedItem, self).__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel(feed_object.feed.title)
        title_label.setFont(QFont('Arial', 18))
        title_label.setStyleSheet("color: #DDD")
        layout.addWidget(title_label)

        number_label = QLabel(str(post_num))
        number_label.setFont(QFont('Arial', 16))
        number_label.setStyleSheet("color: #AAA")
        layout.addStretch(1)
        layout.addWidget(number_label)

        self.setLayout(layout)

class RSSArticleItem(QWidget):

    def __init__(self, post):
        super(RSSArticleItem, self).__init__()

        self.post_id = post.id
        self.post_link = post.link

        date = ""
        try:
            date = "[%d-%02d-%02d]" % (post.published_parsed.tm_year, post.published_parsed.tm_mon, post.published_parsed.tm_mday)
        except Exception:
            pass

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 0, 0)

        post_info_widget = QWidget()
        post_box = QHBoxLayout()
        post_box.setSpacing(10)
        post_box.setContentsMargins(0, 0, 0, 0)

        date_label = QLabel(date)
        date_label.setFont(QFont('Arial', 18))
        post_box.addWidget(date_label)

        title_label = QLabel(post.title)
        title_label.setFont(QFont('Arial', 18))
        post_box.addWidget(title_label)

        author_label = QLabel("(" + post.author + ")")
        author_label.setFont(QFont('Arial', 16))
        post_box.addWidget(author_label)

        post_box.addStretch(1)

        post_info_widget.setLayout(post_box)

        description_doc = QTextDocument()
        description_doc.setHtml(post.description)
        description_label = QLabel(self.truncate_description(description_doc.toPlainText()))
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #333")
        description_label.setFont(QFont("Arial", 16))

        layout.addWidget(post_info_widget)
        layout.addWidget(description_label)

        self.setLayout(layout)

    def truncate_description(self, text):
        return (text[:90] + ' ...') if len(text) > 90 else text

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    w = RSSReaderWidget()
    w.resize(1920, 1080)
    w.show()

    fetchThread = FetchRSSThread()
    fetchThread.fetch_rss.connect(w.handle_rss)
    fetchThread.start()

    sys.exit(app.exec_())
