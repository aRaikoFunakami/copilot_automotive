from pathlib import Path
from bs4 import BeautifulSoup
from starlette.requests import Request
from starlette.responses import HTMLResponse
import pandas as pd
import urllib.parse

# CSVロード（初回のみメモリ読み込み）
VIDEO_CSV_PATH = Path(__file__).parent / 'dummy_data' / 'trailer_db.csv'
video_df = pd.read_csv(VIDEO_CSV_PATH)

async def page_video(request: Request):
    title_raw = request.path_params['title']
    # タイトルはURLエンコードされてくるのでデコード
    title = urllib.parse.unquote(title_raw)

    # title検索
    video_row = video_df[video_df['title'] == title]

    if video_row.empty:
        return HTMLResponse(f"<h1>Video not found for title: {title}</h1>", status_code=404)

    # iframe抽出＆加工
    iframe_html = video_row.iloc[0]['iframe']
    soup = BeautifulSoup(iframe_html, 'html.parser')
    iframe_tag = soup.find('iframe')

    if iframe_tag:
        # フルスクリーン化
        iframe_tag['width'] = '100%'
        iframe_tag['height'] = '100%'
        iframe_tag.attrs.pop('style', None)
        
        # YouTube autoplay対応
        iframe_src = iframe_tag['src']
        if '?' in iframe_src:
            iframe_tag['src'] = iframe_src + '&autoplay=1&enablejsapi=1&mute=1&controls=0'
        else:
            iframe_tag['src'] = iframe_src + '?autoplay=1&enablejsapi=1&mute=1&controls=0'

        iframe_tag['allow'] = "autoplay; encrypted-media;" 
        processed_iframe = str(iframe_tag)
    else:
        return HTMLResponse("<h1>Invalid iframe data</h1>", status_code=500)

    # フルスクリーンHTML組み立て
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                height: 100%;
                background-color: black;
            }}
            iframe {{
                border: none;
                width: 100%;
                height: 100%;
            }}
        </style>
    </head>
    <body>
        {processed_iframe}
    </body>
    </html>
    """
    return HTMLResponse(html_content)