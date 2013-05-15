import gevent
import logging
from grobot import GRobot


def main():
    # Show the browser window.Open the webkit inspector.
    robot = GRobot(display=True, develop=False, log_level=logging.DEBUG, loading_timeout=10, operate_timeout=10)

    # In China,people can only using proxy to access google.
    robot.set_proxy('socks5://127.0.0.1:7070')

    #Open google
    robot.open('http://www.google.com/')

    #Type out project and search.
    robot.type('name=q', 'GRobot github')
    robot.click('name=btnK', expect_loading=True)

    for i in xrange(1, 10):
        # Waiting for the ajax page loading.

        robot.wait_for_xpath("//tr/td[@class='cur' and text()='%s']" % i)

        if u'https://github.com/DYFeng/GRobot' in robot.content:
            print 'The porject in page', i
            break

        # Click the Next link.We don't use expect_loading.Because it's ajax loading,not page loading.
        robot.click("xpath=//span[text()='Next']")

    else:
        print "Can not found.Make a promotion for it."

    # Wait forever.
    robot.wait_forever()


if __name__ == '__main__':
    gevent.spawn(main).join()