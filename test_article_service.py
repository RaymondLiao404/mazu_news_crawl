from services.article_service import ArticleService

TEST_CASES = {
    'cna': {
        'url': 'https://www.cna.com.tw/news/asoc/202603290103.aspx',
        'fallback_text': '',
        'must_not_contain': ['下載中央社', '本網站之文字'],
        'min_length': 200,
    },
    'setn': {
        'url': 'https://www.setn.com/News.aspx?NewsID=1814641',
        'fallback_text': '',
        'must_not_contain': ['延伸閱讀'],
        'min_length': 200,
    },
    'yahoo': {
        'url': 'https://tw.news.yahoo.com/%E5%A4%A7%E7%94%B2%E5%AA%BD%E7%A5%96%E9%81%B6%E5%A2%83%E5%BD%B0%E5%8C%96%E7%99%BB%E5%A0%B4-%E8%AD%A6%E5%AE%AE%E5%BB%9F%E8%81%AF%E6%89%8B%E7%B0%BD%E5%85%AC%E7%B4%84%E9%98%B2%E8%A1%9D%E7%AA%81-130201334.html',
        'fallback_text': '',
        'must_not_contain': ['加入為 Google 偏好來源', '將 Yahoo 設為首選來源'],
        'min_length': 200,
    },
    'ltn': {
        'url': 'https://news.ltn.com.tw/news/Changhua/breakingnews/5386307',
        'fallback_text': '',
        'must_not_contain': ['請繼續往下閱讀', '熱門推播'],
        'min_length': 200,
    },
    'udn': {
        'url': 'https://udn.com/news/story/7327/9409228',
        'fallback_text': '',
        'must_not_contain': [],
        'min_length': 80,
    },
    'sunmedia': {
        'url': 'https://sunmedia.tw/news/collaborative/2acUgQRl2gSuldPntgr9btUK4mmfKahkpZSFUMtNIIUC4U3WdIUjKIoe8AxhAA8QMUFOyxA3',
        'fallback_text': '',
        'must_not_contain': ['閱讀原文'],
        'min_length': 150,
    },
}

service = ArticleService()
all_passed = True

for name, case in TEST_CASES.items():
    content = service.fetch_article_content(case['url'], fallback_text=case['fallback_text'])
    print(f'[{name}] length={len(content)}')

    if len(content) < case['min_length']:
        print(f'FAIL: {name} content too short')
        all_passed = False

    for text in case['must_not_contain']:
        if text in content:
            print(f'FAIL: {name} contains unwanted text: {text}')
            all_passed = False

if not all_passed:
    raise SystemExit(1)

print('ALL TESTS PASSED')
