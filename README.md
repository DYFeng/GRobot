GRobot  [![Build Status](https://travis-ci.org/DYFeng/GRobot.png)](https://travis-ci.org/DYFeng/GRobot)
======

*GRobot is still under development and I love to refactor.So,control your risks.*

GRobot is a powerful web robot based on gevent.
This project comes from [Ghost.py](http://jeanphix.me/Ghost.py),which I have rewrote most of the code inside, and changed its name to GRobot.

```python
import gevent
from grobot import GRobot

def test():
    robot = GRobot()
    robot.open("http://www.yahoo.com")
    assert 'yahoo' in robot.content()

gevent.spawn(test).join()
```

What it can and can't do
==========================

## Can do ##

- Can set up the socks5/http{s} proxy.
- Can simulate *ALL* the operations of hunman beings.
- Can run webkit plugin.
- Can evaluate javascript.
- Can grab the web page as image.
- Can run on a GUI-Less server(by install xvfb).

## Can't do ##

- Can't operate Flash.
- Can't run without PyQt and gevent
- Can't get back http status code.
- Can't transport human to the Mars.



Installation
==============

First you need to install [PyQt](http://www.riverbankcomputing.co.uk/software/pyqt/intro).

In Ubuntu

    sudo apt-get install python-qt4

Install gevent from the development version.

    pip install http://gevent.googlecode.com/files/gevent-1.0b3.tar.gz#egg=gevent

Install Flask for unittest(optional).

    pip install Flask

Install GRobot using pip.

    pip install GRobot

How to use
============

## Quick start ##

First of all, you need a instance of GRobot in greenlet:

```python
import gevent
from grobot import GRobot

def test():
    robot = GRobot()
    #do something

gevent.spawn(test).join()
```


## Element selector ##

Element selector tell GRobot which HTML element a command refers to.
The format of a selector is:

    selectorType=argument

We support the following strategies for locating elements:

- **identifier** = *id* : Select the element with the specified @id attribute.
If no match is found, select the first element whose @name attribute is id.
(This is normally the default; see below.)
- **id** = *id* : Select the element with the specified @id attribute.
- **name** = *name* : Select the first element with the specified @name attribute.
- **xpath** = *xpathExpression* : Locate an element using an XPath expression.

        xpath=//img[@alt='The image alt text']
        xpath=//table[@id='table1']//tr[4]/td[2]
        xpath=//a[contains(@href,'#id1')]
        xpath=//a[contains(@href,'#id1')]/@class
        xpath=(//table[@class='stylee'])//th[text()='theHeaderText']/../td
        xpath=//input[@name='name2' and @value='yes']
        xpath=//*[text()="right"]
- **link** = *textPattern* : Select the link (anchor) element which contains text matching the specified pattern.

        link=The link text
- **css** = *cssSelectorSyntax* : Select the element using css selectors.
Please refer to [CSS2 selectors](http://www.w3.org/TR/CSS2/selector.html) for more information.

        css=a[href="#id3"]
        css=span#firstChild + span

## Option Selector ##

When you using [GRobot.select](#select-options) to deal with `select` tag,option selector tell GRobot which option you want.
The format of a selector is:

    selectorType=argument

We support the following strategies for locating elements:

- **text** = *text* : Match options based on their the visible text.(This is normally the default.)
- **id** = *id* : Match options based on their @id attribute.
- **name** = *name* : Match options based on their @name attribute.
- **value** = *value* : Match options based on their values.



## Open a web page ##

GRobot provide a method that open web page the following way:

    robot.open('http://my.web.page')

## Web page actions ###

We have three shortcut method.

    robot.reload()
    robot.forward()
    robot.back()

If you want more action,check in [Qt Document](http://qt-project.org/doc/qt-4.8/qwebpage.html#WebAction-enum)

    robot.trigger_action('SelectAll)

## Execute javascript ##

Executing javascripts inside webkit frame is one of the most interesting features provided by GRobot:

    result = robot.evaluate( "document.getElementById('my-input').getAttribute('value');")

As many other GRobot methods, you can pass an extra parameter that tells GRobot you expect a page loading:

    robot.evaluate( "document.getElementById('link').click();", expect_loading=True)

## Dealing with forms ##

### Type the text ###
Simulating human typing.

    robot.type('id=blog_content',u'Hello,world.I'm Tom.\n你好,世界.我是无名氏\n')

Type key by key,only ASCII character allowed.

    robot.key_clicks('id=blog_content','Hello,world.\rToday is good for sleep.')

### Select options ###

Select the options those match [selector](option-selector) from `select` tag.

Single selectbox.

    robot.select('name=sex','text=Male')

Multiple selectbox.

    robot.select('id=like',[
        ('apple',True),
        ('orange',False),
        ('banana',True),
    ])

### Set the checkbox ###

You can specify the state of checkbox.

Check it.

    robot.check('id=agree')

Uncheck it.

    robot.check('id=agree',False)


### Click something ###

Click the first element which selected by selector.

    robot.click("xpath=//input[@type='submit']")

Click a point of the absolute position (1500,36).

    robot.click_at(1500,36)

### Move the mouse ###

Move your mouse to first element which selected by selector.

    robot.move_to('css=#button')

Move your mouse to the absolute position (500,300).

    robot.move_at(500,300)

### Setup input file ###

Selenium can't access the `<input type='file'/>` tag.You can't use selenium to set up a file type input.

    robot.choose_file('id=file-upload', '/tmp/file')

## Waiters ##

GRobot provides several methods for waiting for specific things before the script continue execution:

### wait_for_page_loaded() ###

That wait until a new page is loaded.

    robot.wait_for_page_loaded()


### wait_for_selector(selector) ###

That wait until a element match the given css selector.

    result = robot.wait_for_selector("ul.results")

### wait_for_text(text) ###

That wait until the given text exists inside the frame.

    result = robot.wait_for_text("My result")





Sample use case
===============

### Post a twitter ###

```python
import gevent
import logging
from grobot import GRobot

USERNAME = 'your twitter username'
PASSWORD = 'your twitter password'

def main():

    robot = GRobot(display=True, log_level=logging.DEBUG, develop=False)
    robot.set_proxy('socks5://127.0.0.1:7070')
    robot.open('https://twitter.com')

    #Login
    robot.key_clicks('id=signin-email',USERNAME)
    robot.key_clicks('id=signin-password',PASSWORD)

    robot.click("xpath=//td/button[contains(text(),'Sign in')]",expect_loading=True)

    #Post a twitter
    robot.key_clicks("id=tweet-box-mini-home-profile","GRobot is too powerful.https://github.com/DYFeng/GRobot")

    #Wait for post success
    while 1:
        robot.click("xpath=//div[@class='module mini-profile']//button[text()='Tweet']")
        try:
            robot.wait_for_text('Your Tweet was posted')
            break
        except :
            #Something go wrong,refresh page.
            if 'refresh the page' in robot.content():
                robot.reload()

    # Wait forever.
    robot.wait_forever()

if __name__ == '__main__':
    gevent.spawn(main).join()
```


### Browsing Google.com and find GRobot project ###

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
    robot.type('name=q','GRobot github')
    robot.click('name=btnK', expect_loading=True)

    for i in xrange(1, 10):
        # Waiting for the ajax page loading.

        robot.wait_for_xpath("//tr/td[@class='cur' and text()='%s']" % i)

        if u'https://github.com/DYFeng/GRobot' in robot.content():
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
```

