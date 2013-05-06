GRobot
======
GRobot is a powerful web robot,base on gevent and slenium.
This project was came from [Ghost.py](http://jeanphix.me/Ghost.py).I changed a lot and renamed to GRobot.

```python
from grobot import GRobot
robot = GRobot()
page, extra_resources = robot.open("http://www.yahoo.com")
assert page.http_status==200 and 'yahoo' in robot.content
```

#Installation#
------------
First you need to install (PyQt)[http://www.riverbankcomputing.co.uk/software/pyqt/intro].

Install gevent from the development version.

    pip install http://gevent.googlecode.com/files/gevent-1.0b3.tar.gz#egg=gevent


Install GRobot using pip.

    pip install GRobot

#How to use#
----------
##Quick start##

First of all, you need a instance of GRobot in greenlet:

```python
import gevent
from grobot import GRobot
def test():
    robot = GRobot()

gevent.spawn(test).join()
```

##Open a web page##

GRobot provide a method that open web page the following way:

    page, resources = ghost.open('http://my.web.page')

This method returns a tuple of main resource (web page) and all loaded resources (such as CSS files, javascripts, images...).

All those resources are backed as HttpResource objects.

At the moment Httpresource objects provide the following attributes:

- url: The resource url.
- http_status: The HTTP response status code.
- headers: The response headers as a dict.



##Execute javascript##

Executing javascripts inside webkit frame is one of the most interesting features provided by GRobot:

result, resources = robot.evaluate( "document.getElementById('my-input').getAttribute('value');")

The return value is a tuple of:

- last javascript last statement result.
- loaded resources (e.g.: when an XHR is fired up).

As many other Ghost methods, you can pass an extra parameter that tells Ghost you expect a page loading:

    page, resources = robot.evaluate( "document.getElementById('link').click();", expect_loading=True)

Then the result tuple wil be the same as the one returned by GRobot.open().

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


##Waiters##
GRobot provides several methods for waiting for specific things before the script continue execution:

###wait_for_page_loaded()###

That wait until a new page is loaded.

    page, resources = robot.wait_for_page_loaded()


###wait_for_selector(selector)###

That wait until a element match the given selector.

    result, resources = robot.wait_for_selector("ul.results")

###wait_for_text(text)###

That wait until the given text exists inside the frame.

    result, resources = robot.wait_for_selector("My result")


##Sample use case##

###Browsing Google.com and find GRobot project###

```python
import gevent
from grobot import GRobot
def main():

    # Show the browser window.Open the webkit inspector.
    robot = GRobot(display=True, develop=True, log_level=logging.DEBUG, loading_timeout=10, operate_timeout=10)

    # In China,people can only using proxy to access google.
    robot.set_proxy('socks5://127.0.0.1:7070')

    #Open google
    page, resources = robot.open('http://www.google.com/')

    assert page.http_status == 200

    # Filter the google logo file
    pattern = re.compile(r"^.*logo.*\.(png|gif)$")

    # Found the logo image.
    logo = filter_resources(pattern, resources)[0].content

    # Save the logo.
    with open('/tmp/google_log.png', 'wb') as f:
        f.write(logo)

    #Type out project and search.
    robot.seleniumChain([
                            ('type', 'name=q', 'GRobot github'),
                            ('click', 'name=btnK')
                        ], expect_loading=True)

    for i in xrange(1, 10):
        # Waiting for the ajax page loading.
        print i

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


#Known Issues#
--------------

- I never plan to support windows.If it works well on windows,that's great.If it not,please help yourselvers.
- It does not support PySide.For now,PySide is still under develop.It lacked some methods.

    










