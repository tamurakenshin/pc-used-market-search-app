"""Offline-first sample catalogue used for UI demos and graceful fallback."""

SAMPLE_PRODUCTS = [
    {
        "id": "demo-001", "title": "Core i7-14700K BOX", "price": 59800,
        "category": "中古PCパーツ", "part_type": "CPU", "condition": "A", "source": "パソコン工房",
        "url": "https://www.pc-koubou.jp/pc/used_intel_cpu_corei7.php", "image": "/assets/cpu.svg",
        "specs": {"brand": "Intel", "cores": 20, "threads": 28, "clock": "3.4GHz", "year": 2023, "tdp": "125W", "codename": "Raptor Lake Refresh", "socket": "LGA1700"},
        "ai": {"grade": "A", "score": 91, "label": "買い", "market_price": 62800, "summary": "相場より約5%安く、保証付きなら有力候補です。"}
    },
    {
        "id": "demo-002", "title": "Ryzen 7 7800X3D", "price": 52800,
        "category": "中古PCパーツ", "part_type": "CPU", "condition": "A", "source": "じゃんぱら",
        "url": "https://www.janpara.co.jp/", "image": "/assets/cpu.svg",
        "specs": {"brand": "AMD", "cores": 8, "threads": 16, "clock": "4.2GHz", "year": 2023, "tdp": "120W", "codename": "Raphael", "socket": "AM5"},
        "ai": {"grade": "A", "score": 88, "label": "適正", "market_price": 51900, "summary": "ゲーム用途で人気が高く、現在の相場レンジ内です。"}
    },
    {
        "id": "demo-003", "title": "GeForce RTX 4070 SUPER 12GB", "price": 79800,
        "category": "中古PCパーツ", "part_type": "GPU", "condition": "B", "source": "ドスパラ",
        "url": "https://www.dospara.co.jp/", "image": "/assets/gpu.svg",
        "specs": {"brand": "NVIDIA", "memory": "12GB", "interface": "PCIe 4.0", "year": 2024},
        "ai": {"grade": "B", "score": 82, "label": "適正", "market_price": 82000, "summary": "価格は良好。ファン異音と保証期間を確認してください。"}
    },
    {
        "id": "demo-004", "title": "Crucial DDR5-5600 32GB (16GB×2)", "price": 11480,
        "category": "新品PCパーツ", "part_type": "メモリ", "condition": "S", "source": "Amazon",
        "url": "https://www.amazon.co.jp/", "image": "/assets/memory.svg",
        "specs": {"brand": "Crucial", "standard": "DDR5", "capacity": "32GB", "speed": "5600MT/s"},
        "ai": {"grade": "S", "score": 95, "label": "買い", "market_price": 13200, "summary": "新品相場より安価で、汎用性の高い構成です。"}
    },
    {
        "id": "demo-005", "title": "Samsung 990 PRO NVMe SSD 2TB", "price": 23800,
        "category": "新品PCパーツ", "part_type": "ストレージ", "condition": "S", "source": "価格.com",
        "url": "https://kakaku.com/pc/", "image": "/assets/storage.svg",
        "specs": {"brand": "Samsung", "standard": "NVMe Gen4", "capacity": "2TB", "speed": "7450MB/s"},
        "ai": {"grade": "S", "score": 93, "label": "買い", "market_price": 25800, "summary": "高性能Gen4モデルとして割安。ヒートシンク有無を確認。"}
    },
    {
        "id": "demo-006", "title": "GALLERIA XA7C-R47 ゲーミングPC", "price": 219800,
        "category": "新品BTO", "part_type": "PC", "condition": "S", "source": "ドスパラ",
        "url": "https://www.dospara.co.jp/", "image": "/assets/pc.svg",
        "specs": {"cpu": "Core i7-14700F", "gpu": "RTX 4070", "memory": "32GB", "storage": "1TB NVMe"},
        "ai": {"grade": "S", "score": 86, "label": "適正", "market_price": 224000, "summary": "構成バランスが良く、WQHDゲーム向けの適正価格です。"}
    },
    {
        "id": "demo-007", "title": "ThinkPad X1 Carbon Gen 10", "price": 89800,
        "category": "中古PC", "part_type": "PC", "condition": "B", "source": "メルカリ",
        "url": "https://jp.mercari.com/", "image": "/assets/laptop.svg",
        "specs": {"cpu": "Core i7-1260P", "memory": "16GB", "storage": "512GB", "display": "14型 WUXGA"},
        "ai": {"grade": "B", "score": 78, "label": "要確認", "market_price": 93000, "summary": "価格は妥当。バッテリー容量と液晶ムラの確認が必要です。"}
    },
    {
        "id": "demo-008", "title": "Mac mini M2 16GB / 512GB", "price": 97800,
        "category": "中古PC", "part_type": "PC", "condition": "A", "source": "Yahoo!フリマ",
        "url": "https://paypayfleamarket.yahoo.co.jp/", "image": "/assets/pc.svg",
        "specs": {"cpu": "Apple M2", "memory": "16GB", "storage": "512GB", "year": 2023},
        "ai": {"grade": "A", "score": 89, "label": "買い", "market_price": 108000, "summary": "メモリ16GB構成として相場より安く、状態良好なら魅力的です。"}
    },
    {
        "id": "demo-009", "title": "Core i5-12400F 動作確認済み", "price": 14500,
        "category": "中古PCパーツ", "part_type": "CPU", "condition": "B", "source": "Yahoo!オークション",
        "url": "https://auctions.yahoo.co.jp/", "image": "/assets/cpu.svg",
        "specs": {"brand": "Intel", "cores": 6, "threads": 12, "clock": "2.5GHz", "year": 2022, "tdp": "65W", "codename": "Alder Lake", "socket": "LGA1700"},
        "ai": {"grade": "B", "score": 84, "label": "買い", "market_price": 17000, "summary": "動作確認済みなら割安。ピン面写真の確認を推奨します。"}
    },
    {
        "id": "demo-010", "title": "Radeon RX 6800 XT 16GB", "price": 43800,
        "category": "中古PCパーツ", "part_type": "GPU", "condition": "C", "source": "ハードオフ",
        "url": "https://netmall.hardoff.co.jp/", "image": "/assets/gpu.svg",
        "specs": {"brand": "AMD", "memory": "16GB", "interface": "PCIe 4.0", "year": 2020},
        "ai": {"grade": "C", "score": 61, "label": "要確認", "market_price": 49000, "summary": "安価ですが使用歴不明。高負荷テスト可否を確認してください。"}
    },
    {
        "id": "demo-011", "title": "27型 WQHD 165Hz ゲーミングモニター", "price": 29800,
        "category": "新品周辺機器", "part_type": "周辺機器", "condition": "S", "source": "ツクモ",
        "url": "https://shop.tsukumo.co.jp/", "image": "/assets/monitor.svg",
        "specs": {"size": "27型", "resolution": "2560×1440", "refresh": "165Hz", "panel": "IPS"},
        "ai": {"grade": "S", "score": 90, "label": "買い", "market_price": 34800, "summary": "WQHD/高リフレッシュIPSとして費用対効果が高いです。"}
    },
    {
        "id": "demo-012", "title": "DDR4-3200 16GB 2枚組 ジャンク", "price": 2980,
        "category": "中古PCパーツ", "part_type": "メモリ", "condition": "ジャンク", "source": "メルカリ",
        "url": "https://jp.mercari.com/", "image": "/assets/memory.svg",
        "specs": {"standard": "DDR4", "capacity": "32GB", "speed": "3200MT/s"},
        "ai": {"grade": "ジャンク", "score": 28, "label": "見送り", "market_price": 6800, "summary": "未検証品。返品不可なら部品取り前提の価格です。"}
    }
]

