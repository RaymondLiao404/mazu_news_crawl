from pydantic import BaseModel


class Settings(BaseModel):
    # API 預設查詢小時數
    default_hours: int = 12
    # API 允許查詢的最大小時數
    max_hours: int = 48
    # 文章抓取並行數，避免一次開太多連線
    fetch_concurrency: int = 8

    # 這些網站直接排除，不進入最終結果
    excluded_domains: list[str] = [
        'n.yam.com',
        'www.kingtop.com.tw',
        'www.taiwanhot.net',
        'www.bella.tw',
        'news.nextapple.com',
        'www.chinatimes.com',  # 中時新聞網直接排除，因為目前該網站阻擋爬蟲，無法穩定抓取正文
        'www.cmoney.tw',       # CMoney 內容品質不符合需求，因此直接排除
        'www.railway.gov.tw',  # 台鐵新聞頁內容擷取不穩定，暫時排除
        'today.line.me',       # LINE TODAY 內容多為動態載入，擷取品質差
        'more-news.tw',        # 墨新聞需登入或反爬，暫時排除
        'applealmond.com',     # 蘋果仁偏整理型內容，先排除
        'tw.sports.yahoo.com', # Yahoo 體育結果容易混入非媽祖新聞
        'www.msn.com',         # MSN 聚合內容較短，先排除
        'news.pchome.com.tw',  # PChome 新聞聚合內容先排除
        'www.thenewslens.com', # 關鍵評論網長篇選摘內容先排除
    ]

    # 大甲媽主題的搜尋詞，同時也作為二次篩選條件
    dajia_terms: list[str] = [
        '大甲媽',
        '大甲鎮瀾宮',
        '大甲媽祖',
        '大甲媽遶境',
    ]

    # 白沙屯媽祖主題的搜尋詞，同時也作為二次篩選條件
    baishatun_terms: list[str] = [
        '白沙屯媽',
        '白沙屯媽祖',
        '白沙屯拱天宮',
        '白沙屯進香',
    ]


settings = Settings()
