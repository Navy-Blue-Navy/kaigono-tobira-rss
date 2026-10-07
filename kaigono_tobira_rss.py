import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta

URL = "https://www.kaigono-tobira.co.jp/information/blog/"
OUTPUT = Path(__file__).parent / "kaigono_tobira.xml"

# ページ取得
response = requests.get(URL, timeout=30)
response.raise_for_status()
response.encoding = response.apparent_encoding

soup = BeautifulSoup(response.text, "html.parser")

new_items = []
seen_urls = set()

for a in soup.find_all("a", href=True):
    text = a.get_text(" ", strip=True)

    if "詳細はこちら" not in text:
        continue

    article_url = urljoin(URL, a["href"])

    if article_url in seen_urls:
        continue

    heading = a.find_previous(["h2", "h3", "h4"])

    if not heading:
        continue

    title = heading.get_text(" ", strip=True)

    if not title:
        continue

    seen_urls.add(article_url)

    new_items.append({
        "title": title,
        "link": article_url,
        "description": "介護の扉ブログ",
        "guid": article_url
    })

# 以前のRSSを読み込む
old_items = []

if OUTPUT.exists():
    try:
        old_tree = ET.parse(OUTPUT)
        old_root = old_tree.getroot()

        for item in old_root.findall("./channel/item"):
            old_items.append({
                "title": item.findtext("title", ""),
                "link": item.findtext("link", ""),
                "description": item.findtext("description", ""),
                "date": item.findtext("pubDate", ""),
                "guid": item.findtext("guid", "")
            })
    except Exception:
        old_items = []

# 新規記事にRSSへ追加した日時を設定
jst = timezone(timedelta(hours=9))
now = datetime.now(jst).strftime("%a, %d %b %Y %H:%M:%S +0900")

existing_guids = {item["guid"] for item in old_items}

for item in new_items:
    if item["guid"] not in existing_guids:
        item["date"] = now

# 新着＋過去記事を合体して重複除去
all_items = []
seen = set()

for item in new_items + old_items:
    if item["guid"] in seen:
        continue

    seen.add(item["guid"])

    # 既存記事でdateがまだ無い場合
    if "date" not in item:
        item["date"] = now

    all_items.append(item)

# 最大200件保存
all_items = all_items[:200]

# RSS作成
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "介護の扉ブログ"
ET.SubElement(channel, "link").text = URL
ET.SubElement(channel, "description").text = "株式会社介護の扉のブログ更新情報"
ET.SubElement(channel, "language").text = "ja"

for item in all_items:
    element = ET.SubElement(channel, "item")

    ET.SubElement(element, "title").text = item["title"]
    ET.SubElement(element, "link").text = item["link"]
    ET.SubElement(element, "description").text = item["description"]
    ET.SubElement(element, "pubDate").text = item["date"]

    guid_element = ET.SubElement(element, "guid")
    guid_element.set("isPermaLink", "false")
    guid_element.text = item["guid"]

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ")

tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)

print("RSS作成成功")
print("今回取得:", len(new_items), "件")
print("RSS保存件数:", len(all_items), "件")
print("保存先:", OUTPUT)

print()
print("取得記事:")
for item in new_items:
    print(item["title"])