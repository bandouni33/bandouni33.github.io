# -*- coding: utf-8 -*-
"""로또신령 홈페이지 생성기 — 정적 HTML(검색엔진이 그대로 읽는 페이지).

입력: 앱 저장소가 내보낸 site_data/data.json(공개 값만) + 앱 저장소의 그림(타로·아이콘)
출력: _site/ (GitHub Pages 배포)

실행: python build.py --data <data.json> --assets <앱 저장소 경로> --out _site
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import shutil
from pathlib import Path
from xml.sax.saxutils import escape as xesc

HERE = Path(__file__).resolve().parent
SITE_URL = "https://bandouni33.github.io"
SITE_NAME = "로또신령"
NAVER_VERIFY = (HERE / "naver_verification.txt").read_text().strip() if (HERE / "naver_verification.txt").exists() else ""
GOOGLE_VERIFY = (HERE / "google_verification.txt").read_text().strip() if (HERE / "google_verification.txt").exists() else ""
DISCLAIMER = "참고·재미용 정보이며 당첨을 보장하지 않습니다. 복권은 만 19세 이상 구매할 수 있습니다."
KST = dt.timezone(dt.timedelta(hours=9))

e = html.escape


# ── 데이터 ────────────────────────────────────────────────────────────
class Data:
    def __init__(self, raw: dict):
        self.raw = raw
        self.latest = raw["latest_round"]
        self.draws = {r[0]: {"round": r[0], "date": r[1], "nums": r[2:8], "bonus": r[8]} for r in raw["draws"]}
        self.ours = {s["round"]: s["rank"] for s in raw.get("our_stats", [])}
        self.balls = raw["balls"]
        self.links = raw["links"]
        self.tarot = raw["tarot"]

    def analyze(self, rnd: int) -> dict:
        nums = self.draws[rnd]["nums"]
        odd = sum(n % 2 for n in nums)
        low = sum(1 for n in nums if n <= 22)
        runs = sum(1 for a, b in zip(nums, nums[1:]) if b == a + 1)
        bands = [sum(1 for n in nums if lo <= n <= hi) for lo, hi in ((1, 10), (11, 20), (21, 30), (31, 40), (41, 45))]
        return {"odd": odd, "even": 6 - odd, "low": low, "high": 6 - low, "sum": sum(nums), "runs": runs,
                "bands": bands}

    def frequency(self, upto: int, window: int | None = None) -> dict[int, int]:
        rs = [r for r in self.draws if r <= upto and (window is None or r > upto - window)]
        cnt = {n: 0 for n in range(1, 46)}
        for r in rs:
            for n in self.draws[r]["nums"]:
                cnt[n] += 1
        return cnt

    def gaps(self, upto: int) -> dict[int, int]:
        last = {n: 0 for n in range(1, 46)}
        for r in sorted(self.draws):
            if r > upto:
                break
            for n in self.draws[r]["nums"]:
                last[n] = r
        return {n: upto - last[n] for n in range(1, 46)}


def date_kr(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{y}년 {int(m)}월 {int(d)}일"


# ── 조각 ──────────────────────────────────────────────────────────────
def ball(d: Data, n: int, size: str = "") -> str:
    b = d.balls[str(n)]
    return (f'<span class="ball {size}" style="background:{b["fill"]};color:{b["text"]}">{n}</span>')


def balls_row(d: Data, rnd: int, size: str = "") -> str:
    dr = d.draws[rnd]
    inner = "".join(ball(d, n, size) for n in dr["nums"])
    return (f'<div class="balls">{inner}<span class="plus" aria-label="보너스">+</span>'
            f'{ball(d, dr["bonus"], size + " bonus")}</div>')


def seal(rnd: int) -> str:
    return f'<div class="seal" aria-hidden="true"><span>제</span><b>{rnd}</b><span>회</span></div>'


def install_block(d: Data) -> str:
    return (f'<section class="install"><h2>로또신령 앱</h2>'
            f'<p>필터로 거른 자동조합, 번개조합, 타로점, 받은 조합 저장까지 앱에서 이어집니다. '
            f'첫 가입 시 500P로 번호 조합을 무료로 체험할 수 있습니다.</p>'
            f'<div class="btns"><a class="btn primary" href="{e(d.links["play"])}" rel="noopener">구글 플레이에서 설치</a>'
            f'<a class="btn" href="{e(d.links["manual"])}" rel="noopener">사용설명서 보기</a></div>'
            f'<p class="small">아이폰은 앱스토어에서 \'로또신령\'을 검색하세요.</p></section>')


def our_block(d: Data, rnd: int | None = None, limit: int = 6) -> str:
    rows = sorted(d.ours.items(), reverse=True)
    if rnd is not None:
        rows = [(r, v) for r, v in rows if r == rnd]
        if not rows:
            return ""
    rows = rows[:limit]
    if not rows:
        return ""
    body = "".join(f'<tr><th scope="row"><a href="/round/{r}/">{r}회</a></th>'
                   + "".join(f"<td>{x:,}</td>" for x in v) + "</tr>" for r, v in rows)
    title = f"로또신령 조합 {rnd}회 성적" if rnd else "로또신령 조합 회차별 성적"
    return (f'<section><h2>{title}</h2>'
            f'<p>앱이 그 회차용으로 만들어 배포한 조합 가운데 실제로 당첨된 개수입니다. 공식 당첨번호로 계산한 값 그대로이며, 앱 자동조합 화면의 배출 표와 같은 숫자입니다.</p>'
            f'<table class="grid"><thead><tr><th scope="col">회차</th><th scope="col">1등</th><th scope="col">2등</th>'
            f'<th scope="col">3등</th><th scope="col">4등</th></tr></thead><tbody>{body}</tbody></table></section>')


def analysis_block(d: Data, rnd: int) -> str:
    a = d.analyze(rnd)
    bands = " · ".join(f"{lab} {c}개" for lab, c in zip(("1번대", "10번대", "20번대", "30번대", "40번대"), a["bands"]))
    return (f'<dl class="facts"><div><dt>홀짝</dt><dd>{a["odd"]} : {a["even"]}</dd></div>'
            f'<div><dt>낮은 수(1~22) : 높은 수</dt><dd>{a["low"]} : {a["high"]}</dd></div>'
            f'<div><dt>번호 합계</dt><dd>{a["sum"]}</dd></div>'
            f'<div><dt>연속 번호</dt><dd>{a["runs"]}쌍</dd></div>'
            f'<div class="wide"><dt>번호대 분포</dt><dd>{bands}</dd></div></dl>')


def tarot_block(d: Data) -> str:
    t = d.tarot
    return (f'<section class="tarot"><img src="/{e(t["image"])}" alt="타로 카드 {e(t["name"])}({e(t["name_en"])})" '
            f'width="180" height="300" loading="lazy">'
            f'<div><h2>{t["round"]}회를 기다리는 이번 주 신령 타로</h2><p class="card-name">{e(t["name"])} '
            f'<span>{e(t["name_en"])}</span></p><p class="quote">{e(t["line"])}</p>'
            f'<p class="small">앱에서 내 카드를 직접 뽑을 수 있습니다.</p></div></section>')


# ── 페이지 틀 ──────────────────────────────────────────────────────────
def sidebar(d: Data, path: str) -> str:
    """모든 페이지 왼쪽 '로또신령 전체 목록'(2026-10-18 사용자 지시) — PC는 항상 보이고, 휴대폰은 [전체 메뉴]로 펼침."""
    def link(href, label, ext=False):
        cur = ' aria-current="page"' if href == path else ""
        rel = ' rel="noopener" target="_blank"' if ext else ""
        return f'<li><a href="{e(href)}"{cur}{rel}>{e(label)}</a></li>'

    site = "".join(link(h, lab) for h, lab in NAV)
    recent = "".join(link(f"/round/{r}/", f"{r}회 당첨번호") for r in sorted(d.draws, reverse=True)[:5])
    manual = "".join(link(m["url"], m["title"], True) for m in d.links.get("manual_posts", []))
    chans = "".join(link(c["url"], c["name"], True) for c in d.links["channels"])
    return (f'<aside class="side" aria-label="로또신령 전체 목록">'
            f'<a class="brand" href="/"><img src="/img/icon.png" alt="" width="36" height="36">로또신령</a>'
            f'<details class="menu" id="menu" open><summary>전체 메뉴</summary>'
            f'<div class="grp"><h3>홈페이지</h3><ul>{site}</ul></div>'
            f'<div class="grp"><h3>최근 회차</h3><ul>{recent}</ul></div>'
            f'<div class="grp"><h3>앱 설치</h3><ul>{link(d.links["play"], "구글 플레이에서 설치", True)}'
            f'<li class="note">아이폰: 앱스토어에서 \'로또신령\' 검색</li></ul></div>'
            f'<div class="grp"><h3>사용설명서</h3><ul>{manual}</ul></div>'
            f'<div class="grp"><h3>공식 채널</h3><ul>{chans}</ul></div></details>'
            f'<script>if(matchMedia("(max-width:899px)").matches)document.getElementById("menu").removeAttribute("open")</script>'
            f'</aside>')


NAV = [("/", "최신 회차"), ("/rounds/", "전체 회차"), ("/stats/", "번호 통계"), ("/tools/prize/", "실수령액 계산"),
       ("/about/", "앱 소개")]


def page(d: Data, path: str, title: str, desc: str, body: str, *, og_image: str = "/img/og.png",
         extra_head: str = "") -> str:
    url = SITE_URL + path
    verify = ""
    if NAVER_VERIFY:
        verify += f'<meta name="naver-site-verification" content="{e(NAVER_VERIFY)}">'
    if GOOGLE_VERIFY:
        verify += f'<meta name="google-site-verification" content="{e(GOOGLE_VERIFY)}">'
    chans = " ".join(f'<a href="{e(c["url"])}" rel="noopener">{e(c["name"])}</a>' for c in d.links["channels"])
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{SITE_URL}{og_image}">
<meta name="theme-color" content="#151b36">{verify}
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME} 회차 소식" href="{SITE_URL}/rss.xml">
<link rel="icon" href="/img/icon.png"><link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">{extra_head}</head>
<body><div class="shell">{sidebar(d, path)}<div class="content">
<main>{body}</main>
<footer><p>{DISCLAIMER}</p><p>공식 채널 {chans}</p>
<p>당첨번호 출처: 동행복권 공식 발표 · 데이터 갱신 {e(d.raw["generated_at"][:10])}</p></footer></div></div></body></html>"""


# ── 페이지들 ───────────────────────────────────────────────────────────
def round_page(d: Data, rnd: int) -> str:
    dr = d.draws[rnd]
    nums = ", ".join(map(str, dr["nums"]))
    prev_ = f'<a href="/round/{rnd - 1}/">← {rnd - 1}회</a>' if rnd - 1 in d.draws else "<span></span>"
    next_ = f'<a href="/round/{rnd + 1}/">{rnd + 1}회 →</a>' if rnd + 1 in d.draws else "<span></span>"
    body = (f'<article class="hero">{seal(rnd)}<div class="title"><h1>제{rnd}회 로또 당첨번호</h1>'
            f'<p class="date">{date_kr(dr["date"])} 추첨</p></div>{balls_row(d, rnd, "big")}</article>'
            f'<section><h2>번호 구성</h2>{analysis_block(d, rnd)}</section>'
            f'{our_block(d, rnd)}{install_block(d)}<nav class="pager" aria-label="회차 이동">{prev_}'
            f'<a href="/rounds/">전체 회차</a>{next_}</nav>')
    title = f"제{rnd}회 로또 당첨번호 {nums} + 보너스 {dr['bonus']} | {SITE_NAME}"
    desc = f"{date_kr(dr['date'])} 추첨 제{rnd}회 로또 6/45 당첨번호는 {nums}, 보너스 {dr['bonus']}입니다. 홀짝·합계·번호대 분석."
    return page(d, f"/round/{rnd}/", title, desc, body)


def index_page(d: Data) -> str:
    rnd = d.latest
    dr = d.draws[rnd]
    recent = "".join(f'<li><a href="/round/{r}/"><span class="r">{r}회</span>{balls_row(d, r, "sm")}</a></li>'
                     for r in sorted(d.draws, reverse=True)[1:11])
    body = (f'<article class="hero">{seal(rnd)}<div class="title"><h1>제{rnd}회 로또 당첨번호</h1>'
            f'<p class="date">{date_kr(dr["date"])} 추첨</p></div>{balls_row(d, rnd, "big")}'
            f'<p class="more"><a href="/round/{rnd}/">{rnd}회 자세히 보기</a></p></article>'
            f'{tarot_block(d)}{our_block(d)}'
            f'<section><h2>지난 회차</h2><ol class="recent">{recent}</ol>'
            f'<p class="more"><a href="/rounds/">1회부터 전체 보기</a></p></section>{install_block(d)}')
    nums = ", ".join(map(str, dr["nums"]))
    return page(d, "/", f"로또 당첨번호 제{rnd}회 | {SITE_NAME}",
                f"최신 제{rnd}회 로또 당첨번호 {nums} + 보너스 {dr['bonus']}. 회차별 당첨번호, 번호 통계, 실수령액 계산, 이번 주 신령 타로.",
                body)


def rounds_page(d: Data) -> str:
    rows = "".join(f'<tr><th scope="row"><a href="/round/{r}/">{r}회</a></th><td>{d.draws[r]["date"]}</td>'
                   f'<td>{" ".join(map(str, d.draws[r]["nums"]))} <span class="b">+{d.draws[r]["bonus"]}</span></td></tr>'
                   for r in sorted(d.draws, reverse=True))
    body = (f'<h1>로또 회차별 당첨번호</h1><p>1회부터 {d.latest}회까지 모든 당첨번호입니다. 회차를 누르면 번호 구성을 볼 수 있습니다.</p>'
            f'<table class="grid list"><thead><tr><th scope="col">회차</th><th scope="col">추첨일</th>'
            f'<th scope="col">당첨번호 + 보너스</th></tr></thead><tbody>{rows}</tbody></table>')
    return page(d, "/rounds/", f"로또 회차별 당첨번호 전체(1~{d.latest}회) | {SITE_NAME}",
                f"로또 6/45 1회부터 {d.latest}회까지 회차별 당첨번호와 보너스 번호 전체 목록.", body)


def stats_page(d: Data) -> str:
    total = d.frequency(d.latest)
    recent = d.frequency(d.latest, 50)
    gaps = d.gaps(d.latest)
    rows = "".join(
        f'<tr><th scope="row">{ball(d, n, "sm")}</th><td>{total[n]}회</td><td>{recent[n]}회</td>'
        f'<td>{"이번 회" if gaps[n] == 0 else f"{gaps[n]}회 전"}</td></tr>' for n in range(1, 46))
    hot = sorted(range(1, 46), key=lambda n: (-recent[n], n))[:6]
    cold = sorted(range(1, 46), key=lambda n: (-gaps[n], n))[:6]
    body = (f'<h1>로또 번호별 출현 통계</h1><p>1회부터 {d.latest}회까지의 공식 당첨번호(보너스 제외)로 셉니다.</p>'
            f'<section class="pair"><div><h2>최근 50회 많이 나온 번호</h2><div class="balls">'
            f'{"".join(ball(d, n) for n in hot)}</div></div><div><h2>가장 오래 안 나온 번호</h2><div class="balls">'
            f'{"".join(ball(d, n) for n in cold)}</div></div></section><h2>번호별 출현 횟수</h2>'
            f'<table class="grid stats"><thead><tr><th scope="col">번호</th><th scope="col">전체 출현</th>'
            f'<th scope="col">최근 50회</th><th scope="col">마지막 출현</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p class="small">과거 출현 횟수는 다음 추첨 결과를 예측하지 않습니다. 매 회차 모든 번호의 확률은 같습니다.</p>')
    return page(d, "/stats/", f"로또 번호별 출현 횟수 통계({d.latest}회 기준) | {SITE_NAME}",
                f"로또 1~45번 번호별 전체 출현 횟수, 최근 50회 출현, 마지막 출현 회차를 {d.latest}회 기준으로 정리.", body)


def prize_page(d: Data) -> str:
    body = """<h1>로또 당첨금 실수령액 계산</h1>
<p>당첨금을 넣으면 세금을 뺀 예상 실수령액을 보여줍니다.</p>
<form class="calc" onsubmit="return false"><label for="amt">당첨금(원)</label>
<input id="amt" inputmode="numeric" autocomplete="off" placeholder="예: 2000000000">
<div class="quick"><button type="button" data-v="5000">5등 5천원</button><button type="button" data-v="50000">4등 5만원</button>
<button type="button" data-v="1500000">3등 약 150만원</button><button type="button" data-v="60000000">2등 약 6천만원</button>
<button type="button" data-v="2000000000">1등 20억원</button></div>
<output id="res" aria-live="polite"></output></form>
<section><h2>계산 기준</h2><ul>
<li>200만원 이하: 세금 없음</li><li>200만원 초과: 3억원까지 22%(소득세 20% + 지방소득세 2%)</li>
<li>3억원 초과분: 33%(소득세 30% + 지방소득세 3%)</li><li>복권 구입비 1,000원은 필요경비로 빼고 계산</li></ul>
<p class="small">예상치입니다. 정확한 세액은 지급처나 국세청에서 확인하세요.</p></section>
<script>
const f=n=>n.toLocaleString('ko-KR');
function calc(v){v=Math.max(0,Math.floor(v||0));if(!v){res.textContent='';return}
let tax=0;if(v>2000000){const b=v-1000;tax=Math.floor(Math.min(b,3e8)*0.22+Math.max(0,b-3e8)*0.33)}
res.innerHTML='세금 <b>'+f(tax)+'원</b><br>예상 실수령액 <b class="big">'+f(v-tax)+'원</b>'}
amt.addEventListener('input',()=>{const v=+amt.value.replace(/[^0-9]/g,'');amt.value=v?f(v):'';calc(v)});
document.querySelectorAll('.quick button').forEach(b=>b.onclick=()=>{amt.value=f(+b.dataset.v);calc(+b.dataset.v)});
</script>"""
    return page(d, "/tools/prize/", f"로또 당첨금 실수령액 계산기(세금 22%·33%) | {SITE_NAME}",
                "로또 1등·2등·3등 당첨금의 세금과 실수령액을 바로 계산합니다. 200만원 이하 비과세, 3억 초과분 33%.", body)


def about_page(d: Data) -> str:
    body = f"""<h1>로또신령 앱 소개</h1>
<p>로또신령은 지난 당첨번호를 바탕으로 번호 조합을 거르고, 매주 신령 타로로 한 주를 점쳐보는 앱입니다.</p>
<section><h2>앱에서 할 수 있는 것</h2><ul>
<li>타로점: 지금 마음을 카드 한 장으로 짚어보기</li>
<li>자동조합: 다음 회차 배포용 조합에서 내 몫을 자동으로 배정받기</li>
<li>번개조합: 고정수·삭제수·행운수를 정해 한 번에 여러 게임 뽑기</li>
<li>구매복권 검증: 산 번호를 QR스캔이나 직접입력으로 넣고, 반대 조건의 조합 만들기</li>
<li>고급필터·통계센터: 필터 규칙과 번호 흐름 보기</li></ul></section>
{our_block(d)}{install_block(d)}"""
    return page(d, "/about/", f"로또신령 앱 소개 | {SITE_NAME}",
                "로또신령 앱 기능 소개: 타로점, 자동조합, 번개조합, 구매복권 검증, 고급필터, 통계센터.", body)


def notfound_page(d: Data) -> str:
    return page(d, "/404.html", f"페이지를 찾을 수 없습니다 | {SITE_NAME}", "요청한 페이지가 없습니다.",
                f'<h1>페이지를 찾을 수 없습니다</h1><p>주소를 확인하거나 <a href="/">최신 회차</a>로 이동하세요.</p>'
                # 토요일 즉시 게시 링크(/round/<다음 회차>/)는 공식 발표 반영 전 약 1시간 동안 페이지가 없다 → 최신 회차로
                f'<script>if(/^\\/round\\/\\d+\\/?$/.test(location.pathname))location.replace("/");</script>')


# ── 검색엔진용 파일 ───────────────────────────────────────────────────
def sitemap(d: Data) -> str:
    today = d.raw["generated_at"][:10]
    urls = [("/", today, "1.0"), ("/rounds/", today, "0.8"), ("/stats/", today, "0.8"),
            ("/tools/prize/", today, "0.6"), ("/about/", today, "0.5")]
    urls += [(f"/round/{r}/", d.draws[r]["date"], "0.7" if r > d.latest - 10 else "0.4") for r in sorted(d.draws, reverse=True)]
    body = "".join(f"<url><loc>{SITE_URL}{p}</loc><lastmod>{m}</lastmod><priority>{pr}</priority></url>"
                   for p, m, pr in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'


def rss(d: Data) -> str:
    items = ""
    for r in sorted(d.draws, reverse=True)[:20]:
        dr = d.draws[r]
        nums = ", ".join(map(str, dr["nums"]))
        pub = dt.datetime.fromisoformat(dr["date"]).replace(hour=21, tzinfo=KST).strftime("%a, %d %b %Y %H:%M:%S %z")
        items += (f"<item><title>제{r}회 로또 당첨번호 {nums} + 보너스 {dr['bonus']}</title>"
                  f"<link>{SITE_URL}/round/{r}/</link><guid>{SITE_URL}/round/{r}/</guid><pubDate>{pub}</pubDate>"
                  f"<description>{xesc(date_kr(dr['date']))} 추첨 제{r}회 로또 당첨번호 {nums}, 보너스 {dr['bonus']}.</description></item>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE_NAME} 회차 소식</title>'
            f"<link>{SITE_URL}/</link><description>로또 회차별 당첨번호</description><language>ko</language>{items}</channel></rss>")


def build(data_path: Path, assets: Path, out: Path) -> list[Path]:
    d = Data(json.loads(data_path.read_text(encoding="utf-8")))
    if out.exists():
        shutil.rmtree(out)
    (out / "img").mkdir(parents=True)
    shutil.copy(HERE / "style.css", out / "style.css")
    from PIL import Image

    icon = assets / "아이콘815.png"
    if icon.exists():
        Image.open(icon).convert("RGBA").resize((192, 192), Image.LANCZOS).save(out / "img/icon.png", optimize=True)
    shutil.copy(HERE / "og.png", out / "img/og.png")
    tsrc = assets / d.tarot["image"]
    if tsrc.exists():
        (out / Path(d.tarot["image"]).parent).mkdir(parents=True, exist_ok=True)
        im = Image.open(tsrc).convert("RGB")
        im.thumbnail((360, 600))
        im.save(out / d.tarot["image"], quality=85, optimize=True)

    written = []

    def w(rel: str, text: str):
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(p)

    w("index.html", index_page(d))
    w("rounds/index.html", rounds_page(d))
    w("stats/index.html", stats_page(d))
    w("tools/prize/index.html", prize_page(d))
    w("about/index.html", about_page(d))
    w("404.html", notfound_page(d))
    for r in d.draws:
        w(f"round/{r}/index.html", round_page(d, r))
    w("sitemap.xml", sitemap(d))
    w("rss.xml", rss(d))
    w("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    key = (HERE / "indexnow_key.txt")
    if key.exists():
        k = key.read_text().strip()
        w(f"{k}.txt", k)
    (out / ".nojekyll").write_text("")
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--assets", required=True, type=Path)
    ap.add_argument("--out", default=HERE / "_site", type=Path)
    a = ap.parse_args()
    files = build(a.data, a.assets, a.out)
    print(f"[완료] {len(files)}개 파일 → {a.out}")
