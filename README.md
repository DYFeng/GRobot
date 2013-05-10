GRobot  [![Build Status](https://travis-ci.org/DYFeng/GRobot.png)](https://travis-ci.org/DYFeng/GRobot)
======

GRobot is a powerful web robot based on gevent and selenium.
This project comes from [Ghost.py](http://jeanphix.me/Ghost.py),which I have rewrote most of the code inside, and changed its name to GRobot.

```python
from grobot import GRobot
robot = GRobot()
robot.open("http://www.yahoo.com")
assert 'yahoo' in robot.content
```

#What it can and can't do#
--------------------------

##Can do##

- Can set up the socks5/http{s} proxy.
- Can simulate *ALL* the operations of hunman beings.
- Can run webkit plugin.
- Can evaluate javascript.
- Can grab the web page as image.
- Can run on a GUI-Less server(by install xvfb).

##Can't do##

- Can't operate Flash.
- Can't run without PyQt and gevent
- Can't get back http status code.
- Can't transport human to the Mars.



#Installation#
-------------

First you need to install [PyQt](http://www.riverbankcomputing.co.uk/software/pyqt/intro).

In Ubuntu

    sudo apt-get install python-qt4

Install gevent from the development version.

    pip install http://gevent.googlecode.com/files/gevent-1.0b3.tar.gz#egg=gevent

Install Flask for unittest(optional).

    pip install Flask

Install GRobot using pip.

    pip install GRobot

#How to use#
------------
##Quick start##

First of all, you need a instance of GRobot in greenlet:

```python
import gevent
from grobot import GRobot

def test():
    robot = GRobot()
    #do something

gevent.spawn(test).join()
```

##Open a web page##

GRobot provide a method that open web page the following way:

    robot.open('http://my.web.page')

This method returns a tuple of main resource (web page) and all loaded resources (such as CSS files, javascripts, images...).

All those resources are backed as HttpResource objects.

At the moment Httpresource objects provide the following attributes:

- url: The resource url.
- http_status: The HTTP response status code.
- headers: The response headers as a dict.



##Execute javascript##

Executing javascripts inside webkit frame is one of the most interesting features provided by GRobot:

    result = robot.evaluate( "document.getElementById('my-input').getAttribute('value');")

The return value is a tuple of:

- last javascript last statement result.

As many other GRobot methods, you can pass an extra parameter that tells GRobot you expect a page loading:

    robot.evaluate( "document.getElementById('link').click();", expect_loading=True)

##Play with selenium##

Selenium is integrated in GRobot.You can using most of commands of selenim.

Here is a full [selenium command reference](http://release.seleniumhq.org/selenium-core/1.0.1/reference.html)

Parameters of `GRobot.selenium`

- command: The [selenium command](http://release.seleniumhq.org/selenium-core/1.0.1/reference.html#actions),such as `click`,`type`,`select`,`dragAndDrop` and so on.You can do everything with it.
- target: The selenium target.It's a varied [selector](http://release.seleniumhq.org/selenium-core/1.0.1/reference.html#locators).
- value: Value for the command.


###Type the text###
Simulating human typing word by word.

    robot.selenium('type','id=username','Tom')

###Select an option###

    robot.selenium('select','name=sex','label=Male')

###Set the checkbox###
You can specify the state of checkboot

    robot.selenium('check','id=agree')
    robot.selenium('uncheck','id=agree')

###Click something###

    robot.selenium('click',"xpath=//input[@type='submit']")


###Drag and drop###
Drag and drop element.

    robot.selenium('dragAndDropToObject',"id=I'm a stone","id=I'm a bottle")


###Setup input file###

Selenium can't access the `<input type='file'/>` tag.You can't use selenium to set up a file type input.

    robot.set_file_input('id=file-upload', '/tmp/file')


##Play without selenium##
Selenium is powerful,but it can't work everythere.You may want to use some native tool.
Not like selenium,the native tool will control your system mouse and keyboard.

##Click##

    robot.click('id=submit_it')

##Type Text##

Typing text word by word.

    robot.type('Hello world.')

Click the dom of selector and type.

    robot.type('Hello world.','id=note-text')

##Waiters##

GRobot provides several methods for waiting for specific things before the script continue execution:

###wait_for_page_loaded()###

That wait until a new page is loaded.

    robot.wait_for_page_loaded()


###wait_for_selector(selector)###

That wait until a element match the given css selector.

    result = robot.wait_for_selector("ul.results")

###wait_for_text(text)###

That wait until the given text exists inside the frame.

    result = robot.wait_for_text("My result")


##Sample use case##

###Post a twitter with native tool###

```python
import gevent
import logging
from grobot import GRobot

USERNAME = 'your twitter username'
PASSWORD = 'your twitter password'


def main():
    robot = GRobot(display=True, log_level=logging.DEBUG, develop=True)
    robot.set_proxy('socks5://127.0.0.1:7070')
    robot.open('https://twitter.com')

    #Login
    robot.type(USERNAME,'id=signin-email')
    robot.type(PASSWORD,'id=signin-password')
    robot.click("xpath=//td/button[contains(text(),'Sign in')]",expect_loading=True)

    #Post a twitter
    robot.click("id=tweet-box-mini-home-profile")
    robot.type("GRobot is too powerful.https://github.com/DYFeng/GRobot",selector="id=tweet-box-mini-home-profile")
    robot.click("xpath=//div[@class='module mini-profile']//button[text()='Tweet']")

    #Wait for post success
    robot.wait_for_text('Your Tweet was posted')

    # Wait forever.
    robot.wait_for(lambda: False, time_for_stop=-1)

if __name__ == '__main__':
    gevent.spawn(main).join()

```


###Browsing Google.com and find GRobot project with selenium###

```python
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
    robot.seleniumChain([
                            ('type', 'name=q', 'GRobot github'),
                            ('click', 'name=btnK')
                        ], expect_loading=True)

    for i in xrange(1, 10):
        # Waiting for the ajax page loading.

        robot.wait_for_xpath("//tr/td[@class='cur' and text()='%s']" % i)

        if u'https://github.com/DYFeng/GRobot' in robot.content:
            print 'The porject in page', i
            break

        # Click the Next link.We don't use expect_loading.Because it's ajax loading,not page loading.
        robot.selenium('click', "xpath=//span[text()='Next']")

    else:
        print "Can not found.Make a promotion for it."

    # Wait forever.
    robot.wait_for(lambda :False,time_for_stop=-1)

if __name__ == '__main__':
    gevent.spawn(main).join()
```













