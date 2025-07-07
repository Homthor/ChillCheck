def parse_cookies(headers):
    cookies = {}
    if "Cookie" in headers:
        cookie_str = headers.get("Cookie")
        pairs = cookie_str.split(";")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.strip().split("=", 1)
                cookies[key] = value
    return cookies

def get_logged_in_user(headers):
    cookies = parse_cookies(headers)
    return cookies.get("user_id")  # строка, нужно будет приводить к int, если надо
