class Config:
    BASE_URL = "https://economics.nankai.edu.cn/"
    FIRST_PAGE = "https://zfxy.nankai.edu.cn/index/important_nes.htm"
    PAGE_TEMPLATE = "https://economics.nankai.edu.cn/jyxw/list{}.htm"
    MAX_PAGES = 80
    MONGODB_URI = 'mongodb://localhost:27017/'
    DB_NAME = 'test'

    SUPPORTED_ATTACHMENTS = [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".mp3", ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
        ".zip", ".rar", ".tar", ".gz", ".bz2", ".7z",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
        ".exe", ".apk", ".dmg",
        ".csv", ".txt", ".rtf",
        ".xls", ".xlsx",
    ]

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    }