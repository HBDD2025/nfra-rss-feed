import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
import time
# --- Selenium Wait Imports ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
# --- Standard Imports ---
import re
import platform
import os
from urllib.parse import urljoin

# --- 定义默认选择器 (确保在使用前定义！) ---
DEFAULT_ITEM_SELECTOR = 'div.panel-row'
DEFAULT_LINK_SELECTOR_IN_ITEM = 'span.title a'
DEFAULT_TITLE_SELECTOR_IN_ITEM = DEFAULT_LINK_SELECTOR_IN_ITEM # 默认标题选择器同链接
DEFAULT_DATE_SELECTOR_IN_ITEM = 'span.date'

# --- 定义页面信息，包含特定选择器 ---
urls = [
    {   # 监管动态 (itemId=915)
        "url": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=914&itemId=915&itemUrl=ItemListRightList.html&itemName=%E7%9B%91%E7%AE%A1%E5%8A%A8%E6%80%81",
        "category": "总局官网-监管动态",
        "item_selector": DEFAULT_ITEM_SELECTOR,
        "link_selector_in_item": DEFAULT_LINK_SELECTOR_IN_ITEM,
        "date_selector_in_item": DEFAULT_DATE_SELECTOR_IN_ITEM
    },
    {   # 领导活动及讲话 (itemId=919)
        "url": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=914&itemId=919&itemUrl=ItemListRightList.html&itemName=%E9%A2%86%E5%AF%BC%E6%B4%BB%E5%8A%A8%E5%8F%8A%E8%AE%B2%E8%AF%9D",
        "category": "总局官网-领导活动及讲话",
        "item_selector": DEFAULT_ITEM_SELECTOR,
        "link_selector_in_item": DEFAULT_LINK_SELECTOR_IN_ITEM,
        "date_selector_in_item": DEFAULT_DATE_SELECTOR_IN_ITEM
    },
    {   # 政策解读 (itemId=917)
        "url": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=914&itemId=917&itemUrl=ItemListRightList.html&itemName=%E6%94%BF%E7%AD%96%E8%A7%A3%E8%AF%BB&itemsubPId=916",
        "category": "总局官网-政策解读",
        "item_selector": DEFAULT_ITEM_SELECTOR,
        "link_selector_in_item": DEFAULT_LINK_SELECTOR_IN_ITEM,
        "date_selector_in_item": DEFAULT_DATE_SELECTOR_IN_ITEM
    },
    {   # 新闻发布会及访谈 (itemId=920) - 使用特定选择器
        "url": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=914&itemId=920&itemUrl=xinwenzixun/xinwenfabu.html&itemName=%E6%96%B0%E9%97%BB%E5%8F%91%E5%B8%83%E4%BC%9A%E5%8F%8A%E8%AE%BF%E8%B0%88",
        "category": "总局官网-新闻发布会及访谈",
        "item_selector": "div.list_txt li", # 这个页面的条目是 li
        "link_selector_in_item": "a",       # li 下的第一个 a
        "title_selector_in_item": "a",      # 标题也在 a 里
        "date_selector_in_item": "span"     # 日期是 li 下的第一个 span
    },
    {   # 统计信息 (itemId=954)
        "url": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=953&itemId=954&itemUrl=ItemListRightList.html&itemName=%E7%BB%9F%E8%AE%A1%E4%BF%A1%E6%81%AF",
        "category": "总局官网-统计信息",
        "item_selector": DEFAULT_ITEM_SELECTOR,
        "link_selector_in_item": DEFAULT_LINK_SELECTOR_IN_ITEM,
        "date_selector_in_item": DEFAULT_DATE_SELECTOR_IN_ITEM
    },
    {   # 征求意见 (itemId=951)
        "url": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=945&itemId=951&itemUrl=ItemListRightList.html&itemName=%E5%BE%81%E6%B1%82%E6%84%8F%E8%A7%81",
        "category": "总局官网-征求意见",
        "item_selector": DEFAULT_ITEM_SELECTOR,
        "link_selector_in_item": DEFAULT_LINK_SELECTOR_IN_ITEM,
        "date_selector_in_item": DEFAULT_DATE_SELECTOR_IN_ITEM
    }
]

# 设置 Selenium Chrome 选项
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

# 初始化 ChromeDriver
print(f"当前操作系统: {platform.system()}")
try:
    service = None
    # --- 确保路径变量在使用前已经被定义 (尽管这里可能不需要显式路径了) ---
    macos_path_arm = '/opt/homebrew/bin/chromedriver'
    macos_path_intel = '/usr/local/bin/chromedriver'
    linux_path = '/usr/local/bin/chromedriver'
    # --- 检查路径并设置 service ---
    if platform.system() == "Darwin": # macOS
        if os.path.exists(macos_path_arm): service = Service(macos_path_arm)
        elif os.path.exists(macos_path_intel): service = Service(macos_path_intel)
    elif platform.system() == "Linux": # GitHub Actions 通常是 Linux
        if os.path.exists(linux_path): service = Service(linux_path)

    # 根据 service 是否被设置来初始化 driver
    if service:
         print(f"尝试使用 ChromeDriver Service: {service.path}")
         driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
         print(f"尝试从系统 PATH 自动查找 ChromeDriver...")
         # 如果没有找到特定路径的 service，或者不是 macOS/Linux，让 Selenium 自动查找
         driver = webdriver.Chrome(options=chrome_options)

    print("ChromeDriver 初始化成功。")
except WebDriverException as e:
    print(f"错误: ChromeDriver 初始化失败。错误信息: {e}")
    exit(1)

# 初始化 RSS Feed
fg = FeedGenerator()
fg.title('国家金融监督管理总局官网综合信息')
fg.link(href="https://www.nfra.gov.cn", rel='alternate')
fg.description('合并国家金融监督管理总局官网多个栏目的最新信息')
fg.language('zh-CN')

all_entries = []
base_url = "https://www.nfra.gov.cn/cn/view/pages/"

for page_info in urls:
    url = page_info["url"]
    category = page_info["category"]
    item_selector = page_info.get("item_selector")
    link_selector = page_info.get("link_selector_in_item")
    title_selector = page_info.get("title_selector_in_item", link_selector)
    date_selector = page_info.get("date_selector_in_item")

    print(f"\n正在抓取页面: {url}")
    print(f"使用选择器 - 条目: '{item_selector}', 链接: '{link_selector}', 标题: '{title_selector}', 日期: '{date_selector}'")

    news_item_elements = []

    try:
        driver.get(url)
        print(f"页面 {url} 初步加载完成，等待第一个条目出现...")
        wait = WebDriverWait(driver, 20)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, item_selector)))
            print(f"找到第一个条目: '{item_selector}'")
            news_item_elements = driver.find_elements(By.CSS_SELECTOR, item_selector)
            print(f"找到 {len(news_item_elements)} 个潜在新闻条目元素。开始处理...")

        except TimeoutException:
            print(f"错误: 在 {url} 等待第一个条目超时 (选择器: '{item_selector}')。跳过此页面。")
            continue
        except Exception as wait_e:
            print(f"错误: 等待或查找条目元素时出错 on {url}: {wait_e}")
            continue

        for item_element in news_item_elements:
            title = ""
            link = ""
            pub_datetime_obj_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            date_found = False
            link_tag = None

            try:
                # 获取链接
                try:
                    link_tag = item_element.find_element(By.CSS_SELECTOR, link_selector)
                    relative_link = link_tag.get_attribute('href')
                    if relative_link:
                        link = urljoin(base_url, relative_link.strip())
                    else: continue
                except NoSuchElementException: continue

                # 获取标题
                try:
                    if title_selector == link_selector and link_tag: title = link_tag.text.strip()
                    else: title_tag = item_element.find_element(By.CSS_SELECTOR, title_selector); title = title_tag.text.strip()
                    if not title and link_tag: title = link_tag.text.strip()
                except NoSuchElementException:
                     try:
                         if link_tag: title = link_tag.text.strip()
                         else: link_tag = item_element.find_element(By.CSS_SELECTOR, link_selector); title = link_tag.text.strip()
                     except NoSuchElementException: continue
                if not title: continue

                # 获取日期
                try:
                    date_element = item_element.find_element(By.CSS_SELECTOR, date_selector)
                    date_str = date_element.text.strip() or date_element.get_attribute('textContent').strip()
                    if date_str:
                        try: naive_dt = datetime.strptime(date_str, '%Y-%m-%d'); pub_datetime_obj_utc = naive_dt.replace(tzinfo=timezone.utc); date_found = True
                        except ValueError as e_parse: print(f"警告: 解析日期字符串 '{date_str}' (来自 {date_selector}) 失败: {e_parse}.")
                except NoSuchElementException: pass

                # 日期备用方案：从链接提取
                if not date_found:
                    date_match_in_url = re.search(r'/(\d{4}-\d{2}-\d{2})/', link)
                    if date_match_in_url:
                        year_month_day_url = date_match_in_url.group(1)
                        try: naive_dt = datetime.strptime(year_month_day_url, '%Y-%m-%d'); pub_datetime_obj_utc = naive_dt.replace(tzinfo=timezone.utc); print(f"信息: 从链接中成功提取并使用日期: {year_month_day_url} (标题: '{title[:30]}...')"); date_found = True
                        except ValueError: pass
                    else:
                         date_match_in_url_alt = re.search(r'/(\d{8})/', link)
                         if date_match_in_url_alt:
                             year_month_day_url_alt = date_match_in_url_alt.group(1)
                             try: naive_dt = datetime.strptime(year_month_day_url_alt, '%Y%m%d'); pub_datetime_obj_utc = naive_dt.replace(tzinfo=timezone.utc); print(f"信息: 从链接中成功提取并使用日期 (YYYYMMDD格式): {year_month_day_url_alt} (标题: '{title[:30]}...')"); date_found = True
                             except ValueError: pass
                if not date_found: print(f"警告: 最终未能找到有效日期 (标题: '{title[:50]}...')。将使用默认日期。")

                all_entries.append({ "title": title, "link": link, "pub_datetime_obj_utc": pub_datetime_obj_utc, "category": category })
            except Exception as item_e: print(f"错误: 处理单个条目时出错: {item_e}。 Item HTML (部分): {item_element.get_attribute('outerHTML')[:200]}"); continue

    except Exception as page_e: print(f"错误: 抓取页面 {url} 失败: {page_e}"); continue

driver.quit()

# 排序
all_entries.sort(key=lambda x: x["pub_datetime_obj_utc"], reverse=False)

beijing_tz = timezone(timedelta(hours=8))

# Feed 生成
for entry in all_entries:
    fe = fg.add_entry()
    fe.title(entry['title']) # 使用原始标题
    fe.link(href=entry['link'])
    fe.category({'term': entry['category']})
    utc_time_obj = entry['pub_datetime_obj_utc']; beijing_time_obj = utc_time_obj.astimezone(beijing_tz); display_time_str_beijing = beijing_time_obj.strftime('%Y-%m-%d 北京时间')
    description_text = f"<p><b>来源：</b>{entry['category']}</p><p><b>发布时间：</b>{display_time_str_beijing}</p><p><b>原始链接：</b><a href='{entry['link']}' target='_blank' rel='noopener noreferrer'>阅读原文</a></p><hr><p>{entry['title']}</p>"
    fe.description(description_text); fe.pubDate(utc_time_obj)

fg.rss_file('nfra_rss.xml', pretty=True)
print(f"\nRSS 文件已生成：nfra_rss.xml")
print(f"总共抓取 {len(all_entries)} 条新闻")