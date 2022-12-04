import sys

from playwright.sync_api import sync_playwright


def extract_openai_session_token(email, password):
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        # ---------------------
        page.goto("https://chat.openai.com/auth/login")
        page.get_by_role("button", name="Log in").click()
        page.get_by_label("Email address").fill(email)
        page.locator("button[name=\"action\"]").click()
        page.get_by_label("Password").click()
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Continue").click()
        # ---------------------
        with page.expect_response('**/auth/session', timeout=3000):
            cookies = context.cookies()
            session_token = [cookie['value'] for cookie in cookies if cookie['name'] == '__Secure-next-auth.session-token'][0]
            print('Your session token is:')
            print(session_token)
            print()
            print('You can now copy and paste it in your config.json file!')


if __name__ == '__main__':
    openai_email = sys.argv[1]
    openai_password = sys.argv[2]
    extract_openai_session_token(openai_email, openai_password)