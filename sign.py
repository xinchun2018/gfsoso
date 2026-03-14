import json
import os
import re
import sys
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value.strip() == ""):
        raise RuntimeError(f"Missing required env: {name}")
    return (value or "").strip()


def create_session():
    # Prefer curl_cffi: browser TLS fingerprint, works better on Cloudflare-protected sites.
    if env("BBS_USE_CURL_CFFI", "1") == "1":
        try:
            from curl_cffi import requests as curl_requests

            return curl_requests.Session(impersonate=env("BBS_IMPERSONATE", "chrome124"))
        except Exception as exc:
            print(f"[WARN] curl_cffi unavailable, fallback. err={exc}")

    if env("BBS_USE_CLOUDSCRAPER", "0") == "1":
        try:
            import cloudscraper

            return cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
        except Exception as exc:
            print(f"[WARN] cloudscraper unavailable, fallback to requests. err={exc}")

    return requests.Session()


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


def login(session, base_url: str, username: str, password: str, loginfield: str) -> None:
    login_url = env("BBS_LOGIN_URL", f"{base_url}/member.php?mod=logging&action=login")
    login_post_url = env("BBS_LOGIN_POST_URL", "")
    questionid = env("BBS_QUESTIONID", "0")
    answer = env("BBS_ANSWER", "")

    r = session.get(login_url, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Open login page failed: HTTP {r.status_code}. body={r.text[:200]}")

    soup = BeautifulSoup(r.text, "html.parser")
    login_form = None
    for f in soup.find_all("form"):
        fid = (f.get("id") or "").lower()
        name = (f.get("name") or "").lower()
        if "loginform" in fid or name == "login":
            login_form = f
            break

    if login_form is None:
        raise RuntimeError("Cannot find login form on login page")

    form_action = login_form.get("action") or ""
    post_url = login_post_url or urljoin(login_url, form_action.replace("&amp;", "&"))

    payload = {}
    for i in login_form.find_all("input"):
        n = i.get("name")
        if not n:
            continue
        payload[n] = i.get("value", "")

    payload.update(
        {
            "username": username,
            "password": password,
            "questionid": questionid,
            "answer": answer,
            "cookietime": payload.get("cookietime", "2592000"),
            "loginfield": loginfield,
            "loginsubmit": payload.get("loginsubmit", "true"),
        }
    )

    headers = {
        "Referer": login_url,
        "X-Requested-With": "XMLHttpRequest",
    }

    lr = session.post(post_url, data=payload, headers=headers, timeout=30)
    if lr.status_code >= 400:
        raise RuntimeError(f"Login submit failed: HTTP {lr.status_code}. body={lr.text[:200]}")

    text = lr.text
    fail_keys = ["登录失败", "密码错误", "login failed", "用户名或密码错误"]
    if any(k in text for k in fail_keys):
        raise RuntimeError(f"Login failed. response={text[:300]}")

    if "action=logout" not in text and "退出登录" not in text:
        home = session.get(base_url + "/", timeout=30)
        if home.status_code >= 400:
            raise RuntimeError(f"Open home failed: HTTP {home.status_code}")
        if "登录" in home.text and username not in home.text:
            print("[WARN] Unable to strongly confirm login from homepage content.")


def sign(session, base_url: str) -> None:
    sign_mode = env("BBS_SIGN_MODE", "auto").lower()

    are_sign_typeid = env("BBS_ARE_SIGN_TYPEID", "1")
    are_sign_url = env("BBS_ARE_SIGN_URL", f"{base_url}/plugin.php?id=are_sign:getaward&typeid={are_sign_typeid}")

    # are_sign plugin: GET endpoint returns a message page (already-signed / success / failure)
    if sign_mode in ("auto", "are_sign"):
        ar = session.get(are_sign_url, timeout=30)
        if ar.status_code < 400 and ar.text:
            soup = BeautifulSoup(ar.text, "html.parser")
            msg = ""
            box = soup.find(id="messagetext")
            if box:
                p = box.find("p")
                if p:
                    msg = p.get_text(strip=True)

            if "已经签到" in msg or "已签到" in msg:
                print(f"[OK] Already signed today. msg={msg}")
                return
            if "签到成功" in msg or "打卡成功" in msg:
                print(f"[OK] Sign success. msg={msg}")
                return
            if sign_mode == "are_sign":
                raise RuntimeError(f"are_sign response not recognized. msg={msg}, status={ar.status_code}")

    # fallback: dsu_paulsign plugin
    sign_page_url = env("BBS_SIGN_PAGE_URL", f"{base_url}/plugin.php?id=dsu_paulsign:sign")
    sign_post_url = env(
        "BBS_SIGN_POST_URL",
        f"{base_url}/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1",
    )

    qdxq = env("BBS_QDXQ", "kx")
    qdmode = env("BBS_QDMODE", "1")
    todaysay = env("BBS_TODAYSAY", "GitHub Actions 自动签到")

    sr = session.get(sign_page_url, timeout=30)
    if sr.status_code >= 400:
        raise RuntimeError(f"Open sign page failed: HTTP {sr.status_code}. body={sr.text[:200]}")

    if has_signed(sr.text):
        print("[OK] Already signed today.")
        return

    if "插件不存在或已关闭" in sr.text:
        raise RuntimeError("dsu_paulsign plugin is not available on this forum.")

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
        "X-Requested-With": "XMLHttpRequest",
    }

    pr = session.post(sign_post_url, data=payload, headers=headers, timeout=30)
    if pr.status_code >= 400:
        raise RuntimeError(f"Sign submit failed: HTTP {pr.status_code}. body={pr.text[:200]}")

    if has_signed(pr.text) or "签到成功" in pr.text or "恭喜你" in pr.text:
        print("[OK] Sign success.")
        return

    raise RuntimeError(f"Sign failed. response={pr.text[:500]}")


def load_accounts():
    raw = env("BBS_ACCOUNTS_JSON", "")
    if raw:
        try:
            data = json.loads(raw)
        except Exception as exc:
            raise RuntimeError(f"BBS_ACCOUNTS_JSON is not valid JSON: {exc}")
        if not isinstance(data, list) or not data:
            raise RuntimeError("BBS_ACCOUNTS_JSON must be a non-empty array.")

        accounts = []
        for i, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise RuntimeError(f"BBS_ACCOUNTS_JSON item #{i} must be an object.")
            username = (item.get("username") or "").strip()
            password = (item.get("password") or "").strip()
            loginfield = (item.get("loginfield") or env("BBS_LOGIN_FIELD", "email")).strip()
            if not username or not password:
                raise RuntimeError(f"BBS_ACCOUNTS_JSON item #{i} missing username/password.")
            accounts.append({"username": username, "password": password, "loginfield": loginfield})
        return accounts

    return [
        {
            "username": env("BBS_USERNAME", required=True),
            "password": env("BBS_PASSWORD", required=True),
            "loginfield": env("BBS_LOGIN_FIELD", "email"),
        }
    ]


def run_one_account(base_url: str, username: str, password: str, loginfield: str) -> None:
    session = create_session()
    try:
        session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            }
        )
        login(session, base_url, username, password, loginfield)
        sign(session, base_url)
    finally:
        close_fn = getattr(session, "close", None)
        if callable(close_fn):
            close_fn()


def main() -> int:
    base_url = env("BBS_BASE_URL", "https://bbs.91bdqu.com").rstrip("/")
    accounts = load_accounts()
    failed = []

    for i, acct in enumerate(accounts, start=1):
        username = acct["username"]
        masked = username[:3] + "***" if len(username) > 3 else "***"
        print(f"[INFO] Account {i}/{len(accounts)}: {masked}")
        try:
            run_one_account(base_url, acct["username"], acct["password"], acct["loginfield"])
        except Exception as exc:
            failed.append(f"{i}:{username}:{exc}")
            print(f"[ERROR] Account {i} failed: {exc}")

    if failed:
        raise RuntimeError("Some accounts failed: " + " | ".join(failed))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
