# YouTube Channel Excel Exporter

برنامه ساده Streamlit برای دریافت اطلاعات عمومی کانال‌ها و ویدئوهای عمومی قابل‌دسترسی و خروجی Excel.

## اجرا
```bash
pip install -r requirements.txt
streamlit run app.py
```

## راه‌اندازی YouTube API
1. در Google Cloud Console یک پروژه بسازید.
2. YouTube Data API v3 را فعال کنید.
3. یک API Key بسازید.
4. کلید را در نوار کناری برنامه وارد کنید یا در Streamlit Secrets با نام `YOUTUBE_API_KEY` ذخیره کنید.

هرگز API Key را در GitHub یا داخل کد قرار ندهید.

## لینک‌های پشتیبانی‌شده
- `https://www.youtube.com/@handle`
- `https://www.youtube.com/channel/UC...`

لینک‌های قدیمی `/c/` و `/user/` با جست‌وجوی YouTube resolve می‌شوند و ممکن است سهمیه بیشتری مصرف کنند.

## خروجی Excel
- `Overview`: خلاصه استخراج و وضعیت/خطای هر کانال
- `Channels`: اطلاعات کانال‌ها
- `All Videos`: یک ردیف برای هر ویدئو

فقط اطلاعات عمومی‌ای صادر می‌شود که YouTube Data API در اختیار می‌گذارد. درآمد، impressions، CTR و watch time خصوصی از این API قابل دریافت نیستند. برخی فیلدها ممکن است مخفی یا خالی باشند.

برنامه فهرست ویدئوهای playlist آپلود کانال را صفحه‌به‌صفحه می‌خواند و عمداً به ۵۰ یا ۱۰۰ ویدئوی اخیر محدود نمی‌شود. سهمیه API و محدودیت منابع میزبانی رایگان ممکن است روی استخراج‌های بسیار بزرگ اثر بگذارد.
