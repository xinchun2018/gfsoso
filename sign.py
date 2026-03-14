import os
import re
import sys
from typing import Optional

import requests
from bs4 import BeautifulSoup


def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value.strip() == ""):
        raise RuntimeError(f"Missing required env: {name}")
    return (value or "").strip()


def get_formhash(html: str) -> Optional[str]:
    patterns = [
        r'name="formhash"\s+value="([^"]+)"',
        r"formhash=([0-9a-zA-Z]+)",
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1)

    soup = BeautifulSoup(html, "html.parser")
    node = soup.find("input", attrs={"name": "formhash"})
    if node and node.get("value"):
        return node["value"]
    return None


def has_signed(html: str) -> bool:
    keys = ["已签到", "今日已签到", "already signed", "succeedhandle_qiandao"]
    return any(k in html for k in keys)


def login(session: requests.Session, base_url: str) -> None:
    username = env("BBS_USERNAME", required=True)
    password = env("BBS_PASSWORD", required=True)
    login_url = env("BBS_LOGIN_URL", f"{base_url}/member.php?mod=logging&action=login")
    login_post_url = env(
        "BBS_LOGIN_POST_URL",
        f"{base_url}/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1",
    )
    questionid = env("BBS_QUESTIONID", "0")
    answer = env("BBS_ANSWER", "")

    r = session.get(login_url, timeout=20)
    r.raise_for_status()
    formhash = get_formhash(r.text)

    payload = {
        "username": username,
        "password": password,
        "questionid": questionid,
        "answer": answer,
        "cookietime": "2592000",
        "loginfield": "username",
    }
    if formhash:
        payload["formhash"] = formhash

    headers = {
        "Referer": login_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "X-Requested-With": "XMLHttpRequest",
    }

    lr = session.post(login_post_url, data=payload, headers=headers, timeout=20)
    lr.raise_for_status()

    text = lr.text
    fail_keys = ["登录失败", "密码错误", "login failed", "用户名或密码错误"]
    if any(k in text for k in fail_keys):
        raise RuntimeError(f"Login failed. response={text[:300]}")

    home = session.get(base_url + "/", timeout=20)
    home.raise_for_status()
    if "登录" in home.text and username not in home.text:
        print("[WARN] Unable to strongly confirm login from homepage content.")


def sign(session: requests.Session, base_url: str) -> None:
    sign_page_url = env("BBS_SIGN_PAGE_URL", f"{base_url}/plugin.php?id=dsu_paulsign:sign")
    sign_post_url = env(
        "BBS_SIGN_POST_URL",
        f"{base_url}/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1",
    )

    qdxq = env("BBS_QDXQ", "kx")
    qdmode = env("BBS_QDMODE", "1")
    todaysay = env("BBS_TODAYSAY", "GitHub Actions 自动签到")

    sr = session.get(sign_page_url, timeout=20)
    sr.raise_for_status()

    if has_signed(sr.text):
        print("[OK] Already signed today.")
        return

    formhash = get_formhash(sr.text)
    if not formhash:
        raise RuntimeError("Cannot find formhash on sign page. Please verify sign page URL and plugin type.")

    payload = {
        "formhash": formhash,
        "qdxq": qdxq,
        "qdmode": qdmode,
        "todaysay": todaysay,
        "fastreply": "0",
    }

    headers = {
        "Referer": sign_page_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "X-Requested-With": "XMLHttpRequest",
    }

    pr = session.post(sign_post_url, data=payload, headers=headers, timeout=20)
    pr.raise_for_status()

    if has_signed(pr.text) or "签到成功" in pr.text or "恭喜你" in pr.text:
        print("[OK] Sign success.")
        return

    raise RuntimeError(f"Sign failed. response={pr.text[:500]}")


def main() -> int:
    base_url = env("BBS_BASE_URL", "https://bbs.91bdqu.com").rstrip("/")

    with requests.Session() as session:
        session.headers.update({"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})

        # Force direct network path: ignore env proxies so requests uses local egress.
        if env("BBS_FORCE_DIRECT", "1") == "1":
            session.trust_env = False
            session.proxies.clear()

        login(session, base_url)
        sign(session, base_url)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
