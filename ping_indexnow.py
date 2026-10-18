# -*- coding: utf-8 -*-
"""새로 바뀐 주소를 네이버·빙(IndexNow)에 알린다. 실패해도 배포는 성공으로 둔다(검색엔진 사정)."""
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = "https://bandouni33.github.io"
KEY = (HERE / "indexnow_key.txt").read_text().strip()
ENDPOINTS = ["https://searchadvisor.naver.com/indexnow", "https://api.indexnow.org/indexnow"]


def main(data_path: str) -> None:
    latest = json.loads(Path(data_path).read_text(encoding="utf-8"))["latest_round"]
    urls = [f"{SITE}/", f"{SITE}/round/{latest}/", f"{SITE}/rounds/", f"{SITE}/stats/"]
    body = json.dumps({"host": "bandouni33.github.io", "key": KEY, "keyLocation": f"{SITE}/{KEY}.txt",
                       "urlList": urls}).encode()
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=15) as r:
                print(ep, r.status)
        except Exception as exc:  # noqa: BLE001
            print(ep, "실패:", exc)


if __name__ == "__main__":
    main(sys.argv[1])
