import gevent
import logging
from grobot import GRobot

USERNAME = 'your twitter username'
PASSWORD = 'your twitter password'


def main():
    robot = GRobot(display=True, log_level=logging.DEBUG, develop=False)

    # Chinese people love proxy.
    robot.set_proxy('socks5://127.0.0.1:7070')

    robot.open('https://twitter.com')

    # Login
    robot.key_clicks('id=signin-email', USERNAME)
    robot.key_clicks('id=signin-password', PASSWORD)

    robot.click("xpath=//td/button[contains(text(),'Sign in')]", expect_loading=True)

    # Post a twitter
    robot.key_clicks("id=tweet-box-mini-home-profile", "GRobot is too powerful.https://github.com/DYFeng/GRobot")

    # Wait for post success
    while 1:
        robot.click("xpath=//div[@class='module mini-profile']//button[text()='Tweet']")
        try:
            robot.wait_for_text('Your Tweet was posted')
            break
        except:
            #Something go wrong,refresh page.
            if 'refresh the page' in robot.content:
                robot.reload()

    # Wait forever.
    robot.wait_forever()


if __name__ == '__main__':
    gevent.spawn(main).join()