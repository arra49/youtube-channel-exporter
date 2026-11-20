import re
from io import BytesIO
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
import pandas as pd
import streamlit as st
import isodate

API = "https://www.googleapis.com/youtube/v3"
S = requests.Session()

st.set_page_config(page_title="YouTube Excel Exporter", page_icon="📊")
st.title("📊 استخراج اطلاعات کانال‌های یوتیوب")
st.write("لینک کانال‌ها را وارد کنید تا اطلاعات عمومی کانال و تمام ویدئوهای عمومی قابل‌دسترسی در فایل Excel ذخیره شود.")

def get_api(endpoint, params, key):
    r = S.get(f"{API}/{endpoint}", params={**params, "key": key}, timeout=45)
    try:
        data = r.json()
    except Exception:
        data = {}
    if r.status_code != 200:
        raise RuntimeError(data.get("error", {}).get("message", r.text[:250]))
    return data

def resolve(raw, key):
    url = raw.strip()
    if not url.startswith(("https://", "http://")):
        url = "https://" + url
    p = urlparse(url)
    if p.netloc.lower().replace("www.", "") not in ("youtube.com", "m.youtube.com"):
        raise ValueError("لینک کانال یوتیوب معتبر نیست.")
    parts = p.path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "channel":
        data = get_api("channels", {"part":"snippet,statistics,contentDetails", "id":parts[1]}, key)
    elif parts and parts[0].startswith("@"):
        data = get_api("channels", {"part":"snippet,statistics,contentDetails", "forHandle":parts[0][1:]}, key)
    elif len(parts) >= 2 and parts[0] in ("c", "user"):
        search = get_api("search", {"part":"snippet", "q":parts[1], "type":"channel", "maxResults":5}, key)
        ids = [x.get("id",{}).get("channelId") for x in search.get("items",[])]
        ids = [x for x in ids if x]
        if not ids:
            raise ValueError("کانال پیدا نشد.")
        data = get_api("channels", {"part":"snippet,statistics,contentDetails", "id":ids[0]}, key)
    else:
        raise ValueError("از لینک‌های @handle یا /channel/UC... استفاده کنید.")
    if not data.get("items"):
        raise ValueError("کانال پیدا نشد یا اطلاعات آن در دسترس نیست.")
    return data["items"][0]

def num(d, k):
    try: return int(d[k]) if k in d else None
    except (ValueError, TypeError): return None

def duration(iso):
    try:
        sec = int(isodate.parse_duration(iso).total_seconds())
        h, rem = divmod(sec, 3600); m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    except Exception: return iso or ""

def collect(ch, key):
    sn, stats = ch.get("snippet",{}), ch.get("statistics",{})
    cid = ch.get("id","")
    uploads = ch.get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
    ids, token = [], None
    while uploads:
        q = {"part":"contentDetails", "playlistId":uploads, "maxResults":50}
        if token: q["pageToken"] = token
        page = get_api("playlistItems", q, key)
        ids += [x.get("contentDetails",{}).get("videoId") for x in page.get("items",[])]
        token = page.get("nextPageToken")
        if not token: break
    rows = []
    for i in range(0, len(ids), 50):
        batch = [x for x in ids[i:i+50] if x]
        if not batch: continue
        data = get_api("videos", {"part":"snippet,statistics,contentDetails","id":",".join(batch)}, key)
        for v in data.get("items",[]):
            s, stt, cd = v.get("snippet",{}), v.get("statistics",{}), v.get("contentDetails",{})
            vid = v.get("id","")
            rows.append({
                "Channel Name":sn.get("title",""), "Channel ID":cid,
                "Video Title":s.get("title",""), "Video ID":vid,
                "Description":s.get("description",""), "Published At":s.get("publishedAt",""),
                "Duration":duration(cd.get("duration","")), "Duration ISO":cd.get("duration",""),
                "Views":num(stt,"viewCount"), "Likes":num(stt,"likeCount"),
                "Comments":num(stt,"commentCount"), "Tags":", ".join(s.get("tags",[])),
                "Category ID":s.get("categoryId",""),
                "Video URL":f"https://www.youtube.com/watch?v={vid}"
            })
    channel_row = {
        "Channel Name":sn.get("title",""), "Channel ID":cid,
        "Custom URL / Handle":sn.get("customUrl",""), "Description":sn.get("description",""),
        "Created At":sn.get("publishedAt",""),
        "Subscribers":None if stats.get("hiddenSubscriberCount") else num(stats,"subscriberCount"),
        "Total Views":num(stats,"viewCount"), "Video Count (API)":num(stats,"videoCount"),
        "Country":sn.get("country",""), "Channel URL":f"https://www.youtube.com/channel/{cid}",
        "Videos Retrieved":len(rows)
    }
    return channel_row, rows

secret = ""
try: secret = st.secrets.get("YOUTUBE_API_KEY", "")
except Exception: pass
with st.sidebar:
    st.header("تنظیمات")
    key_input = st.text_input("YouTube API Key", value=secret, type="password")
    st.caption("کلید را در GitHub منتشر نکنید؛ در این کادر یا Streamlit Secrets وارد کنید.")

urls = st.text_area("لینک کانال‌ها (هر لینک در یک خط)", height=170,
                    placeholder="https://www.youtube.com/@Google\nhttps://www.youtube.com/channel/UC...")
st.caption("لینک‌های @handle و /channel/UC... پشتیبانی می‌شوند. لینک‌های قدیمی /c/ و /user/ ممکن است سهمیه بیشتری مصرف کنند.")

if st.button("شروع استخراج و ساخت Excel", type="primary", use_container_width=True):
    key = key_input.strip()
    links = list(dict.fromkeys(x.strip() for x in re.split(r"[\n,]+", urls) if x.strip()))
    if not key: st.error("کلید YouTube API را وارد کنید.")
    elif not links: st.error("حداقل یک لینک کانال وارد کنید.")
    else:
        channels, videos, statuses = [], [], []
        bar, msg = st.progress(0), st.empty()
        for i, link in enumerate(links, 1):
            msg.write(f"در حال پردازش {i} از {len(links)}")
            try:
                ch = resolve(link, key)
                cr, vr = collect(ch, key)
                channels.append(cr); videos.extend(vr)
                statuses.append({"Input URL":link,"Channel Name":cr["Channel Name"],"Channel ID":cr["Channel ID"],
                                  "Status":"موفق","Videos Retrieved":len(vr),"Error":""})
            except Exception as e:
                statuses.append({"Input URL":link,"Channel Name":"","Channel ID":"",
                                  "Status":"خطا","Videos Retrieved":0,"Error":str(e)})
            bar.progress(i/len(links))
        summary = pd.DataFrame([
            {"Item":"Extraction time (UTC)","Value":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")},
            {"Item":"Input channels","Value":len(links)},
            {"Item":"Successful channels","Value":len(channels)},
            {"Item":"Failed channels","Value":sum(x["Status"]=="خطا" for x in statuses)},
            {"Item":"Total videos retrieved","Value":len(videos)}
        ])
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            summary.to_excel(writer, sheet_name="Overview", index=False)
            pd.DataFrame(statuses).to_excel(writer, sheet_name="Overview", index=False, startrow=len(summary)+3)
            pd.DataFrame(channels).to_excel(writer, sheet_name="Channels", index=False)
            pd.DataFrame(videos).to_excel(writer, sheet_name="All Videos", index=False)
        out.seek(0)
        st.success(f"پایان استخراج: {len(channels)} کانال و {len(videos)} ویدئو.")
        if any(x["Status"]=="خطا" for x in statuses):
            st.warning("برخی کانال‌ها خطا داشتند؛ جزئیات در شیت Overview ثبت شده است.")
        st.download_button("⬇️ دانلود فایل Excel", out.getvalue(),
                           file_name=f"youtube_export_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
