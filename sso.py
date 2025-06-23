import requests
import re

class LoginError(Exception):
    """登录失败异常"""
    pass

class API(requests.Session):
    def __init__(self, username: str = None, password: str = None):
        super().__init__()
        self.trust_env = False
        self.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            }
        )
        self.username = username
        self.password = password

    def login(self, url: str = None, username: str = None, password: str = None):
        if username is None:
            username = self.username
            if password is None:
                password = self.password
        if username is None or password is None:
            raise LoginError("username and password required")
        if url is None:
            loginUrl = "https://sso.buaa.edu.cn/login"
            loginHtml = self.get(loginUrl).text
        else:
            res = super().get(url)
            loginUrl = res.url
            loginHtml = res.text
        if "tip-text" in loginHtml:
            raise LoginError(
                "login failed: "
                + re.search(
                    r'<div class="tip-text">[^<\/div>]+<\/div>', loginHtml
                ).group(0)[24:-6]
            )
        if 'input name="execution"' not in loginHtml:
            return
        execution = re.search(r'<input name="execution" value="[^"]+', loginHtml).group(
            0
        )[31:]
        res = super().post(
            loginUrl,
            data={
                "username": username,
                "password": password,
                "submit": "登录",
                "type": "username_password",
                "execution": execution,
                "_eventId": "submit",
            },
            allow_redirects=False,
        )
        if res.status_code != 302:
            raise LoginError("login failed")
        while res.status_code == 302:
            location = res.headers.get("Location")
            if not location:
                raise LoginError("login failed: 未找到Location跳转头")
            res = super().get(location, allow_redirects=False)
            if '?token=' in location:
                self.token = location.split('?token=')[1]
                super().get(location)
                return

    def logout(self):
        return (
            self.get(
                "https://sso.buaa.edu.cn/logout", allow_redirects=False
            ).status_code
            == 302
        )

    def get(self, url: str, retry: int = 3, **kwargs):
        if "sso.buaa.edu.cn" in url:
            return super().get(url, **kwargs)
        if retry == 0:
            raise requests.exceptions.RetryError("retry limit exceeded")
        res = super().get(url, **kwargs)
        if "sso.buaa.edu.cn" in res.url:
            self.login()
            return self.get(url, retry=retry - 1, **kwargs)
        return res

    def post(self, url: str, retry: int = 3, **kwargs):
        if "sso.buaa.edu.cn" in url:
            return super().post(url, **kwargs)
        if retry == 0:
            raise requests.exceptions.RetryError("retry limit exceeded")
        res = super().post(url, **kwargs)
        if "sso.buaa.edu.cn" in res.url:
            self.login()
            return self.post(url, retry=retry - 1, **kwargs)
        return res

    def call(self, url: str, retry: int = 3, **kwargs):
        headers = kwargs.get("headers", {})
        headers.update({"X-Requested-With": "XMLHttpRequest"})
        kwargs["headers"] = headers
        return self.post(url, retry=retry, **kwargs)
