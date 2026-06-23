# PC Scout AI

新品・中古PC／パーツの価格を横断検索し、相場と商品の状態を評価するローカルWebアプリです。UIはブラウザで動作し、バックエンドはPython標準ライブラリだけでも起動できます。SeleniumとGroqは環境変数で有効化できます。

## 起動

```powershell
python app.py
```

ブラウザで `http://127.0.0.1:8765` を開きます。初期状態ではデモデータを表示するため、APIキーや追加パッケージなしでUIを確認できます。

## Selenium巡回を有効にする

```powershell
python -m pip install -r requirements.txt
$env:ENABLE_LIVE_SCRAPING="1"
$env:SCRAPER_WORKERS="3"        # 同時巡回数（任意）
$env:SCRAPER_CACHE_SECONDS="180" # 同一検索のキャッシュ秒数（任意）
python app.py
```

Chrome、Edge、Safari（macOS）の順に利用可能なブラウザを自動選択します。「LIVE巡回」をオンにして検索してください。対象サイトの規約、robots.txt、アクセス頻度を確認し、個人利用の範囲で使用してください。

## Groqを有効にする

```powershell
$env:GROQ_API_KEY="gsk_..."
$env:GROQ_MODEL="llama-3.3-70b-versatile"  # 任意
python app.py
```

キーはブラウザへ送られず、サーバー側からGroq APIを呼び出します。キー未設定またはAPI失敗時は、価格中央値と商品状態に基づくローカル評価へ自動的に切り替わります。

## テスト

```powershell
python -m unittest discover -s tests -v
```

## 構成

- `app.py`: HTTP API・静的ファイル配信
- `scraper.py`: Selenium巡回、正規化、重複除去
- `ai_service.py`: Groq評価・出品文生成、ローカルフォールバック
- `sample_data.py`: オフライン表示用サンプル
- `static/`: HTML/CSS/JavaScriptと商品画像

