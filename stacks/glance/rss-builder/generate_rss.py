#!/usr/bin/env python3
import re
from datetime import datetime
from xml.sax.saxutils import escape

rss_path = "/rss/index.xml"
md_path = "/updates/updates.md"

with open(md_path, "r", encoding="utf-8") as f:
    content = f.read()

entries = re.findall(r"## (\d{4}-\d{2}-\d{2}) - (.+?)\n(.+?)(?=\n## |\Z)", content, re.DOTALL)

rss_items = ""
for date_str, title, description in entries:
    pubdate = datetime.strptime(date_str, "%Y-%m-%d").strftime("%a, %d %b %Y 12:00:00 GMT")
    rss_items += f"""  <item>
    <title>{escape(title.strip())}</title>
    <link>http://rss/index.xml#{escape(title.strip().replace(" ", "-").lower())}</link>
    <pubDate>{pubdate}</pubDate>
    <description>{escape(description.strip())}</description>
  </item>\n"""

rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Updates serveur</title>
  <link>http://rss/index.xml</link>
  <description>Changelog des services Tellserv</description>
{rss_items}</channel>
</rss>
"""

with open(rss_path, "w", encoding="utf-8") as f:
    f.write(rss)

print("Flux RSS généré.")
