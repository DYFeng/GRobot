# -*- coding: utf-8 -*-
import gevent
import sys, time
from urlparse import urlparse

from StringIO import StringIO

from functools import wraps
from gevent.lock import RLock

import os
import re
import codecs
import logging
import subprocess
import tempfile
from cookielib import Cookie, LWPCookieJar

import lxml.html as HTML

import sip

sip.setapi(u'QVariant', 2)

from PyQt4.Qt import Qt
from PyQt4.QtTest import QTest

from PyQt4 import QtWebKit
from PyQt4.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkProxy, \
    QNetworkCookieJar, QNetworkDiskCache, QNetworkProxyFactory, QNetworkCookie
from PyQt4.QtWebKit import QWebSettings, QWebPage, QWebView, QWebInspector
from PyQt4.QtCore import QSize, QByteArray, QUrl, QDateTime, \
    QtCriticalMsg, QtDebugMsg, QtFatalMsg, QtWarningMsg, QPoint, QEvent

from PyQt4.QtGui import QApplication, QImage, QPainter, QMouseEvent


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(filename)s:%(lineno)d] [%(name)s::%(funcName)s] %(message)s',
                    datefmt='%H:%M:%S')

logger = logging.getLogger('GRobot')

default_user_agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0"

_pattern_type = type(re.compile("", 0))


def can_load_page(func):
    """Decorator that specifies if user can expect page loading from
    this action. If expect_loading is set to True, GRobot will wait
    for page_loaded event.

    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        expect_loading = False
        if 'expect_loading' in kwargs:
            expect_loading = kwargs['expect_loading']
            del kwargs['expect_loading']
        if expect_loading:
            self._loaded = False
            func(self, *args, **kwargs)
            return self.wait_for_page_loaded()
        return func(self, *args, **kwargs)

    return wrapper


def have_a_break(func):
    """Decorator that specifies if user can expect page loading from
    this action. If expect_loading is set to True, GRobot will wait
    for page_loaded event.

    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if 'sleep' in kwargs:
            interval = kwargs['sleep']
            del kwargs['sleep']
        else:
            sleep = self.sleep

        result = func(self, *args, **kwargs)
        gevent.sleep(sleep)
        return result

    return wrapper


def singleton(class_):
    class class_w(class_):
        _instance = None

        def __new__(class_, *args, **kwargs):
            if class_w._instance is None:
                class_w._instance = super(class_w, class_).__new__(class_,
                                                                   *args,
                                                                   **kwargs)
                class_w._instance._sealed = False
            return class_w._instance

        def __init__(self, *args, **kwargs):
            if self._sealed:
                return
            super(class_w, self).__init__(*args, **kwargs)
            self._sealed = True

    class_w.__name__ = class_.__name__
    return class_w


class XPath(object):
    def __init__(self, content=None):
        if content is not None:
            if isinstance(content, HTML.HtmlElement):
                self.__parser_content = content
            else:
                self.compile(content)

    def compile(self, content):
        self.__parser_content = HTML.document_fromstring(content)

    def execute(self, *arg, **kwargs):
        try:
            return map(lambda x: unicode(x) if isinstance(x, basestring) else x,
                       self.__parser_content.xpath(*arg, **kwargs))
        except Exception:
            return None


class GRobotNetworkAccessManager(QNetworkAccessManager):
    def __init__(self, robot, parent=None):
        self._robot = robot
        super(GRobotNetworkAccessManager, self).__init__(parent)

    def createRequest(self, op, req, outgoingData=None):
        req.setRawHeader('Accept-Language', self._robot.accept_language)
        return super(GRobotNetworkAccessManager, self).createRequest(op, req, outgoingData)


class GRobotWebPage(QtWebKit.QWebPage):
    """Overrides QtWebKit.QWebPage in order to intercept some graphical
    behaviours like alert(), confirm().
    Also intercepts client side console.log().
    """

    def __init__(self, robot, parent=None):
        super(GRobotWebPage, self).__init__(parent)
        self._robot = robot
        self.setNetworkAccessManager(GRobotNetworkAccessManager(self._robot, self))

    def javaScriptConsoleMessage(self, message, line, source):
        """Prints client console message in current output stream."""

        super(GRobotWebPage, self).javaScriptConsoleMessage(message, line,
                                                            source)
        log_type = "error" if "Error" in message else "info"
        getattr(logger, log_type)("%s(%d): %s" % (source or '<unknown>', line, message))

    def chooseFile(self, frame, suggested_file=None):
        if self._robot._upload_file and os.path.isfile(self._robot._upload_file):
            return self._robot._upload_file
        else:
            logger.error('upload file %s is not exist.' % self._robot._upload_file)

    def javaScriptAlert(self, frame, message):
        """Notifies GRobot for alert, then pass."""

        self._robot._alert = message
        self._robot.popup_messages = message
        logger.debug("alert('%s')" % message)

    def javaScriptConfirm(self, frame, message):
        """Checks if GRobot is waiting for confirm, then returns the right
        value.
        """

        if self._robot._confirm_expected is None:
            raise Exception('You must specified a value to confirm "%s"' %
                            message)
        confirmation, callback = self._robot._confirm_expected
        logger.debug("confirm('%s')" % message)
        self._robot._confirm_expected = None
        self._robot.popup_messages = message

        if callback is not None:
            return callback()
        return confirmation

    def javaScriptPrompt(self, frame, message, defaultValue, result=None):
        """Checks if GRobot is waiting for prompt, then enters the right
        value.
        """

        if self._robot._prompt_expected is None:
            raise Exception('You must specified a value for prompt "%s"' %
                            message)

        result_value, callback, confirm = self._robot._prompt_expected
        logger.debug("prompt('%s')" % message)

        if callback is not None:
            result_value = callback()

        if result_value == '':
            logger.warning("'%s' prompt filled with empty string" % message)

        result.append(result_value)

        self._robot._prompt_expected = None
        self._robot.popup_messages = message

        return confirm

    def setUserAgent(self, user_agent):
        self.user_agent = user_agent

    def userAgentForUrl(self, url):
        return self.user_agent


@singleton
class QtMainLoop(object):
    """The Qt main loop thread.Singleton pattern.

    """

    def __init__(self, app=None):
        self._app = app
        self._stop = False
        self._greenlet = None
        self._instance = None

    def stop(self):

        self._app.exit()
        #TODO:This is very ugry to hard-code terminate time.But I can't find another better way.
        # gevent.sleep(1)
        self._stop = True
        self._greenlet.join(timeout=10)
        self._greenlet = None
        sip.delete(self._app)


    def start(self):
        if self._greenlet is None:
            self._stop = False
            self._greenlet = gevent.spawn(self.run)

    def run(self):
        """Main event loop of Qt.
        """
        self._app.processEvents()
        try:
            while not self._stop:
                # GRobot._app.processEvents()
                while self._app.hasPendingEvents():
                    self._app.processEvents()
                gevent.sleep(0.01)
        except Exception, e:
            logger.error(e)
        logger.debug('Goodbye GRobot')


class HttpResource(object):
    """Represents an HTTP resource.

    """

    def __init__(self, reply, cache, content=None):
        self.url = reply.url()
        self.request_url = unicode(reply.request().url().toString())
        self.content = content
        if self.content is None:
            # Tries to get back content from cache
            _buffer = cache.data(self.url)
            if _buffer is not None:
                content = _buffer.readAll()
                try:
                    self.content = unicode(content)
                except UnicodeDecodeError:
                    self.content = content

        self.http_status = reply.attribute(
            QNetworkRequest.HttpStatusCodeAttribute)

        self.url = self.url.toString()

        logger.debug("Resource loaded: %s %s" % (self.url, self.http_status))
        self.headers = {}
        for header in reply.rawHeaderList():
            self.headers[unicode(header)] = unicode(reply.rawHeader(header))
        self._reply = reply


class OperateTimeout(Exception):
    pass


class LoadingTimeout(Exception):
    pass


class confirm:
    """Statement that tells GRobot how to deal with javascript confirm().

    @param confirm: A bollean that confirm.
    @param callable: A callable that returns a boolean for confirmation.
    """

    def __init__(self, robot, confirm=True, callback=None):
        self.confirm = confirm
        self.callback = callback
        self._robot = robot

    def __enter__(self):
        self._robot._confirm_expected = (self.confirm, self.callback)

    def __exit__(self, type, value, traceback):
        self._robot.wait_for(lambda: self._robot._confirm_expected is None)


class prompt:
    """Statement that tells Ghost how to deal with javascript prompt().

    @param value: A string value to fill in prompt.
    @param callback: A callable that returns the value to fill in.
    """

    def __init__(self, robot, value='', confirm=True, callback=None):
        self.value = value
        self.callback = callback
        self.confirm = confirm
        self._robot = robot

    def __enter__(self):
        self._robot._prompt_expected = (self.value, self.callback, self.confirm)

    def __exit__(self, type, value, traceback):
        gevent.sleep(2)
        self._robot.wait_for(lambda: self._robot._confirm_expected is None)


class GRobot(object):
    _loop = None
    _liveRobot = 0
    _app = None
    exit_lock = RLock()

    def __init__(self, user_agent=default_user_agent, operate_timeout=10, loading_timeout=60, log_level=logging.WARNING,
                 display=False, viewport_size=(1024, 768), accept_language='en,*', ignore_ssl_errors=True,
                 cache_dir=os.path.join(tempfile.gettempdir(), "GRobot"),
                 image_enabled=True, plugins_enabled=False, java_enabled=False, javascript_enabled=True,
                 plugin_path=None, develop=False, proxy=None, sleep=0.5, jquery_namespace='GRobot'):
        """GRobot manages a QWebPage.
    
        @param user_agent: The default User-Agent header.
        @param operate_timeout: Operation timeout.
        @param loading_timeout: The page loading timeout.
        @param log_level: The optional logging level.
        @param display: A boolean that tells GRobot to displays UI.
        @param viewport_size: A tupple that sets initial viewport size.
        @param accept_language: Set the webkit accept language. 
        @param ignore_ssl_errors: A boolean that forces ignore ssl errors.
        @param cache_dir: A directory path where to store cache datas.
        @param image_enabled: Enable images.
        @param plugins_enabled: Enable plugins (like Flash).
        @param java_enabled: Enable Java JRE.
        @param javascript_enabled: Enable Javascript.
        @param plugin_path: Array with paths to plugin directories (default ['/usr/lib/mozilla/plugins'])
        @param develop: Enable the Webkit Inspector.
        @param proxy: Set a Socks5,HTTP{S} Proxy
        @param sleep: Sleep `sleep` second,after operate
        @param jquery_namespace: Set the jQuery namespace.
        """

        GRobot.exit_lock.acquire()
        logger.setLevel(log_level)

        plugin_path = plugin_path or ['/usr/lib/mozilla/plugins', ]

        GRobot._liveRobot += 1

        self.develop = develop
        self.inspector = None
        self.plugin = False
        self.exitLoop = False

        self.set_proxy(proxy)

        self.sleep = sleep
        self.jquery_namespace = jquery_namespace
        self.popup_messages = None
        self.accept_language = accept_language

        self._loaded = True

        self._confirm_expected = None
        self._prompt_expected = None
        self._upload_file = None
        self._alert = None

        self.http_resources = []

        self.user_agent = user_agent

        self.loading_timeout = loading_timeout
        self.operate_timeout = operate_timeout

        self.ignore_ssl_errors = ignore_ssl_errors

        if not sys.platform.startswith('win') and not 'DISPLAY' in os.environ \
            and not hasattr(GRobot, 'xvfb'):
            try:
                os.environ['DISPLAY'] = ':99'
                GRobot.xvfb = subprocess.Popen(['Xvfb', ':99'])
            except OSError:
                raise Exception('Xvfb is required to a GRobot run oustside ' + \
                                'an X instance')

        self.display = display

        if not GRobot._app:
            GRobot._app = QApplication.instance() or QApplication(['GRobot'])
            if plugin_path:
                for p in plugin_path:
                    GRobot._app.addLibraryPath(p)

        self.page = GRobotWebPage(self, GRobot._app)

        QtWebKit.QWebSettings.setMaximumPagesInCache(0)
        QtWebKit.QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.LocalStorageEnabled, True)

        self.page.setForwardUnsupportedContent(True)

        # Page signals
        self.page.loadFinished.connect(self._page_loaded)
        self.page.loadStarted.connect(self._page_load_started)
        self.page.unsupportedContent.connect(self._unsupported_content)

        self.manager = self.page.networkAccessManager()

        #TODO:Think about how to handle the network accessible signal
        #self.manager.networkAccessibleChanged.connect()

        self.manager.finished.connect(self._request_ended)
        self.manager.sslErrors.connect(self._on_manager_ssl_errors)

        # Cache
        self.cache = QNetworkDiskCache()
        self.cache.setCacheDirectory(cache_dir)

        self.manager.setCache(self.cache)

        # Cookie jar
        self.cookie_jar = QNetworkCookieJar()
        self.manager.setCookieJar(self.cookie_jar)

        # User Agent
        self.page.setUserAgent(self.user_agent)

        self.page.networkAccessManager().authenticationRequired \
            .connect(self._authenticate)
        self.page.networkAccessManager().proxyAuthenticationRequired \
            .connect(self._authenticate)

        self.main_frame = self.page.mainFrame()

        self.webview = None

        self.viewport_size = viewport_size

        self.webview = QtWebKit.QWebView()
        self.webview.setPage(self.page)

        self.webview.show() if display else self.webview.hide()

        self.set_viewport_size(*viewport_size)

        self.page.settings().setAttribute(QtWebKit.QWebSettings.PluginsEnabled, plugins_enabled)
        self.page.settings().setAttribute(QtWebKit.QWebSettings.JavaEnabled, java_enabled)
        self.page.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, self.develop)

        self.enable_image = image_enabled
        self.enable_javascript = javascript_enabled

        #always open link in current window instead of new window
        self.page.setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.page.linkClicked.connect(self._link_clicked)

        #start the qt main loop
        GRobot._loop = QtMainLoop(GRobot._app)
        GRobot._loop.start()
        GRobot.exit_lock.release()

    @property
    def popup_messages(self):
        return self._popup_messages

    @popup_messages.setter
    def popup_messages(self, value):
        self._popup_messages = unicode(value)


    @property
    def url(self):
        return unicode(self.main_frame.url().toString())


    @property
    def content(self):
        """Returns current frame HTML as a string."""
        return unicode(self.page.currentFrame().toHtml())

    @property
    def cookies(self):
        """Returns all cookies."""
        return self.cookie_jar.allCookies()


    @property
    def enable_image(self):
        """Disable the page images can speed up page loading.

        """
        return self._enable_image

    @enable_image.setter
    def enable_image(self, value):
        self.page.settings().setAttribute(QWebSettings.AutoLoadImages, value)
        self._enable_image = value

    #TODO:It seems not work?
    # @enable_image.deleter
    # def enable_image(self):
    #     raise NotImplemented

    @property
    def enable_javascript(self):
        """Disable the page javascript can speed up page loading.

        """
        return self._enable_javascript

    @enable_javascript.setter
    def enable_javascript(self, value):
        self.page.settings().setAttribute(QWebSettings.JavascriptEnabled, value)
        self._enable_javascript = value


    def open(self, address, method='get', headers=None, auth=None, body=None,
             default_popup_response=None):
        """Opens a web page.

        @param address: The resource URL.
        @param method: The Http method.
        @param headers: An optional dict of extra request hearders.
        @param auth: An optional tupple of HTTP auth (username, password).
        @param body: An optional string containing a payload.
        @param default_popup_response: the default response for any confirm/
        alert/prompt popup from the Javascript (replaces the need for the with
        blocks)
        """

        headers = headers or {}

        body = body or QByteArray()
        try:
            method = getattr(QNetworkAccessManager,
                             "%sOperation" % method.capitalize())
        except AttributeError:
            raise Exception("Invalid http method %s" % method)
        request = QNetworkRequest(QUrl(address))
        request.CacheLoadControl = 0
        for header in headers:
            request.setRawHeader(header, headers[header])
        self._auth = auth
        self._auth_attempt = 0  # Avoids reccursion
        self.page.mainFrame().load(request, method, body)
        self._loaded = False

        if default_popup_response is not None:
            self._prompt_expected = (default_popup_response, None)
            self._confirm_expected = (default_popup_response, None)

        return self.wait_for_page_loaded()

    def set_viewport_size(self, width, height):
        """Sets the page viewport size.

        @param width: An integer that sets width pixel count.
        @param height: An integer that sets height pixel count.
        """

        if self.display:
            self.webview.resize(QSize(width, height))
        self.page.setViewportSize(QSize(width, height))


    def set_proxy(self, proxy=None):
        """Set the proxy or using system configuration as None,supported socks5 http{s}.

        @param proxy: Example:socks5://username:password@127.0.0.1:7070
        """
        proxy_type = None
        if proxy:
            parse = urlparse(proxy)
            scheme = parse.scheme
            hostname = parse.hostname
            port = parse.port
            username = parse.username or ''
            password = parse.password or ''

            if scheme == 'socks5':
                proxy_type = QNetworkProxy.Socks5Proxy
            elif scheme in ('http', 'https'):
                proxy_type = QNetworkProxy.HttpProxy

        if proxy_type:
            self.page.networkAccessManager().setProxy(
                QNetworkProxy(proxy_type, hostname, port, username, password)
            )
        else:
            QNetworkProxyFactory.setUseSystemConfiguration(True)

    def first_element_position(self, selector):
        try:
            return self.elements_position(selector)[0]
        except IndexError:
            logger.warning("Can't locate selector " + selector)
            return None


    def elements_position(self, selector):
        """Get the position of elements whose match selector

        @param selector:
        @return: position of QPoint
        """
        attr, pattern, val = self.parser_selector(selector, attr='identifier')

        strip = lambda v: v.strip()

        if pattern:
            val = locals()[pattern](val)


        def identifier(query):
            return id(query) or name(query)

        def name(query):
            return css("*[name='%s']" % query)

        def id(query):
            return css('#' + query)

        def link(query):
            return xpath(u"//a[@text()='%s']" % query.replace("\'", "\\'"))

        def css(query):
            result = []
            for ele in self.main_frame.findAllElements(query):
                if not ele.isNull():
                    result.append(ele.geometry().center())
            return result

        def xpath(query):
            positions = self.evaluate(u"""
            function GetAbsoluteLocationEx(element)
            {
                if ( arguments.length != 1 || element == null )
                {
                    return null;
                }
                var elmt = element;
                var offsetTop = elmt.offsetTop;
                var offsetLeft = elmt.offsetLeft;
                var offsetWidth = elmt.offsetWidth;
                var offsetHeight = elmt.offsetHeight;
                while( elmt = elmt.offsetParent )
                {
                      // add this judge
                    if ( elmt.style.position == 'absolute' || elmt.style.position == 'relative'
                        || ( elmt.style.overflow != 'visible' && elmt.style.overflow != '' ) )
                    {
                        break;
                    }
                    offsetTop += elmt.offsetTop;
                    offsetLeft += elmt.offsetLeft;
                }
                return { absoluteTop: offsetTop, absoluteLeft: offsetLeft,
                    offsetWidth: offsetWidth, offsetHeight: offsetHeight };
            }
            result=[];
            for (var r = document.evaluate('%s', document, null, 5, null), n; n = r.iterateNext();) {
            pos=GetAbsoluteLocationEx(n)
            result.push([pos.absoluteLeft+pos.offsetWidth/2.0,pos.absoluteTop+pos.offsetHeight/2.0]);
            }
            result
            """ % query.replace("\'", "\\'"))

            return map(lambda x: QPoint(*tuple(x)), positions)

        return locals()[attr](val)


    def _move_page_center_to(self, qpoint):
        size = self.page.viewportSize()
        self.main_frame.setScrollPosition(qpoint - QPoint(size.width(), size.height()) / 2)


    def reload(self):
        """Reload page.

        @return:
        """

        self.trigger_action('Reload', expect_loading=True)

    def back(self):
        self.trigger_action('Back')

    def forward(self):
        self.trigger_action('Forward')


    @can_load_page
    def trigger_action(self, action):
        """Trigger QWebPage::WebAction

        @param action:
        """
        self.page.triggerAction(getattr(QWebPage, action))


    def parser_selector(self, selector, attr=None, pattern=None, val=None):
        index = selector.find('=')

        if index <= 0:
            val = selector
        else:
            attr = selector[:index]
            value_ = selector[index + 1:]
            index = value_.find(':')

            if index > 0:
                pattern = value_[:index]

            val = value_[index + 1:]

        return attr, pattern, val


    @can_load_page
    @have_a_break
    def click(self, selector):
        qpoint = self.first_element_position(selector)
        if qpoint:
            return self._click_position(qpoint)


    @can_load_page
    def _click_position(self, qpoint):
        self._move_page_center_to(qpoint)
        self.webview.repaint()
        pos = qpoint - self.main_frame.scrollPosition()

        self._move_to_position(pos)
        QTest.mouseClick(self.webview, Qt.LeftButton, pos=pos)
        gevent.sleep(1)
        return pos


    def qpoint_to_tuple(self, qpoint):
        return qpoint.x(), qpoint.y()

    @have_a_break
    def move_to(self, selector):
        qpoint = self.first_element_position(selector)
        if qpoint:
            self._move_to_position(qpoint)
            return qpoint_to_tuple(qpoint)

    def move_at(self, x, y):
        self._move_to_position(QPoint(x, y))

    def _move_to_position(self, qpoint):
        QTest.mouseMove(self.webview, pos=qpoint)
        return qpoint

    @have_a_break
    def click_at(self, x, y):
        self._click_position(QPoint(x, y))

    @have_a_break
    def key_clicks(self, selector, text):
        if selector:
            self.click(selector)
        QTest.keyClicks(self.webview, text, delay=50)

    @have_a_break
    def type(self, selector, text):
        position = self.click(selector)

        ele = self._hit_element_from(position)

        ele.setFocus()
        ele.evaluateJavaScript(
            u"""
            core.events.setValue(this, '%s')
            """ % (text.replace("\n", "\\n").replace("\'", "\\'"))
        )
        logger.debug('type %s %s' % (selector, text))


    def _hit_element_from(self, position):
        return self.main_frame.hitTestContent(position).element()

    def first_element(self, selector):
        position = self.first_element_position(selector)
        if position:
            return self.main_frame.hitTestContent(position).element(), position


    def wait_forever(self):
        self.wait_for(lambda: False, time_for_stop=-1)

    @have_a_break
    def check(self, selector, checked=True):
        ele, position = self.first_element(selector)
        if ele and ele.tagName() == 'INPUT':
            if ele.attribute('type') in ['checkbox', 'radio']:
                ele_checked = ele.attribute('checked') == 'checked' or False
                if ele_checked != checked:
                    self._click_position(position)
            else:
                raise ValueError, "%s is not a checkbox or radio" % selector

    @have_a_break
    def select(self, selector, value):

        def _select(query, select_by, select):
            select.evaluateJavaScript(u"""
            triggerEvent(this, 'focus', false);
            var changed = false;
            var optionToSelect = '%s';
            for (var i = 0; i < this.options.length; i++) {
                var option = this.options[i];
                if (option.selected && option.%s != optionToSelect) {
                    option.selected = false;
                    changed = true;
                }
                else if (!option.selected && option.%s == optionToSelect) {
                    option.selected = true;
                    changed = true;
                }
            }

            if (changed) {
                triggerEvent(this, 'change', true);
            }
            """ % ( query.replace("\'", "\\'"), select_by, select_by))

        def _add_selection(query, select_by, select, selected):
            select.evaluateJavaScript(u"""
            triggerEvent(this, 'focus', false);
            var optionToSelect = '%s';
            for (var i = 0; i < this.options.length; i++) {
                var option = this.options[i];
                if (option.%s == optionToSelect)
                {
                    option.selected = %s;
                    triggerEvent(this, 'change', true);
                }

            }
            """ % ( query.replace("\'", "\\'"), select_by, selected and 'true' or 'false'))

        ele, position = self.first_element(selector)

        if ele and ele.tagName() == 'SELECT':
            ele.setFocus()

            if ele.attribute('multiple') == 'multiple':
                assert isinstance(value, list)
                for value_, selected in value:
                    attr, pattern, val = self.parser_selector(value_, attr='text')
                    _add_selection(val, attr, ele, selected)
            else:
                attr, pattern, val = self.parser_selector(value, attr='text')
                _select(val, attr, ele)


    def choose_file(self, selector, file):
        self._upload_file = file
        self.click(selector)
        self._upload_file = None


    def capture(self, selector=None):
        """Capture the images of selector.

        @param selector: Css selector.
        @return: Images
        """

        elements = self.main_frame.documentElement().findAll(selector)
        imgs = []

        for element in elements:
            geo = element.geometry()
            img = QImage(geo.width(), geo.height(), QImage.Format_ARGB32)
            painter = QPainter(img)
            element.render(painter)
            painter.end()
            imgs.append(img)

        return imgs

    def capture_to(self, path, selector=None):
        """Capture the images of selector to files.

        @param path: File path with index suffix.
        @param selector: Css selector.
        @return: The paths of saving.
        """

        _, ext = os.path.splitext(path)
        ext = ext[1:]

        imgs = self.capture(selector)
        result = []
        for index, img in enumerate(imgs):
            filepath = '%s.%s' % (path, index)
            if img.save(filepath, ext.upper()):
                result.append(filepath)

        return result

    def capture_to_buf(self, selector=None):
        """capture the images of selector to StringIO

        @param selector: Css selector.
        @return: The StringIO list.
        """

        images = self.capture(selector)
        result = []

        for image in images:
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.ReadWrite)
            image.save(buf, 'jpg')
            stream = StringIO(str(buf.buffer()))
            result.append(stream)

        return result


    @can_load_page
    def evaluate(self, script):
        """Evaluates script in page frame.

        @param script: The script to evaluate.
        """
        result = self.main_frame.evaluateJavaScript("%s" % script)
        # if isinstance(result,QString):
        #     result=unicode(result)
        return result

    def evaluate_js_file(self, path, encoding='utf-8'):
        """Evaluates javascript file at given path in current frame.
        Raises native IOException in case of invalid file.

        @param path: The path of the file.
        @param encoding: The file's encoding.
        """
        self.evaluate(codecs.open(path, encoding=encoding).read())

    def __del__(self):
        """Depend on the CG of Python.
        """
        self._exit()


    def delete_cookies(self):
        """Deletes all cookies."""
        self.cookie_jar.setAllCookies([])

    def exists(self, selector):
        """Checks if element exists for given selector.

        @param string: The element selector.
        """
        return not self.main_frame.findFirstElement(selector).isNull()


        #TODO: Still not work.

    #     def remove_css(self):
    #         """Remore the css,speed up page loading.
    #
    #         @return:
    #         """
    #
    #         return self.evaluate("""var targetelement="link";//determine element type to create nodelist from
    # var targetattr="href"//determine corresponding attribute to test for
    # var allsuspects=document.getElementsByTagName(targetelement)
    # for (var i=allsuspects.length; i>=0; i--){ //search backwards within nodelist for matching elements to remove
    # if (allsuspects[i] && allsuspects[i].getAttribute(targetattr)!=null )
    # allsuspects[i].parentNode.removeChild(allsuspects[i]); //remove element by calling parentNode.removeChild()
    # }
    #         """)


    def filter_resources(self, pattern):
        """Filter resources with pattern.

        @param pattern: Match pattern.
        @param resources:
        @return: @raise:
        """
        if isinstance(pattern, basestring):
            is_match = lambda x: pattern == x
        elif isinstance(pattern, _pattern_type):
            is_match = lambda x: pattern.match(x)
        elif hasattr(pattern, '__call__'):
            is_match = pattern
        else:
            raise TypeError, 'pattern must be one of str,re.compile,callable'
        return filter(lambda x: is_match(x.request_url), self.http_resources)[:]


    def save(self, path):
        """Save current page content to the path.
        
        @param path: The path to save.
        """
        f = open(path, 'w')
        f.write(self.content.encode('utf-8'))
        f.close()

    def global_exists(self, global_name):
        """Checks if javascript global exists.

        @param global_name: The name of the global.
        """
        return self.evaluate('!(typeof %s === "undefined");' %
                             global_name)


    def load_cookies( self, cookie_storage, keep_old=False ):
        """load from cookielib's CookieJar or Set-Cookie3 format text file.

        @param cookie_storage: file location string on disk or CookieJar instance.
        @param keep_old: Don't reset, keep cookies not overridden.
        """

        def toQtCookieJar( PyCookieJar, QtCookieJar ):
            allCookies = QtCookieJar.cookies if keep_old else []
            for pc in PyCookieJar:
                qc = toQtCookie(pc)
                allCookies.append(qc)
            QtCookieJar.setAllCookies(allCookies)

        def toQtCookie(PyCookie):
            qc = QNetworkCookie(PyCookie.name, PyCookie.value)
            qc.setSecure(PyCookie.secure)
            if PyCookie.path_specified:
                qc.setPath(PyCookie.path)
            if PyCookie.domain != "":
                qc.setDomain(PyCookie.domain)
            if PyCookie.expires != 0:
                t = QDateTime()
                t.setTime_t(PyCookie.expires)
                qc.setExpirationDate(t)
                # not yet handled(maybe less useful):
            #   py cookie.rest / QNetworkCookie.setHttpOnly()
            return qc

        if cookie_storage.__class__.__name__ == 'str':
            cj = LWPCookieJar(cookie_storage)
            cj.load()
            toQtCookieJar(cj, self.cookie_jar)
        elif cookie_storage.__class__.__name__.endswith('CookieJar'):
            toQtCookieJar(cookie_storage, self.cookie_jar)
        else:
            raise ValueError, 'unsupported cookie_storage type.'


    def save_cookies(self, cookie_storage):
        """Save to cookielib's CookieJar or Set-Cookie3 format text file.

        @param cookie_storage: file location string or CookieJar instance.
        """

        def toPyCookieJar(QtCookieJar, PyCookieJar):
            for c in QtCookieJar.allCookies():
                PyCookieJar.set_cookie(toPyCookie(c))

        def toPyCookie(QtCookie):
            port = None
            port_specified = False
            secure = QtCookie.isSecure()
            name = str(QtCookie.name())
            value = str(QtCookie.value())
            v = str(QtCookie.path())
            path_specified = bool(v != "")
            path = v if path_specified else None
            v = str(QtCookie.domain())
            domain_specified = bool(v != "")
            domain = v
            domain_initial_dot = v.startswith('.') if domain_specified else None
            v = long(QtCookie.expirationDate().toTime_t())
            # Long type boundary on 32bit platfroms; avoid ValueError
            expires = 2147483647 if v > 2147483647 else v
            rest = {}
            discard = False
            return Cookie(0, name, value, port, port_specified, domain
                , domain_specified, domain_initial_dot, path, path_specified
                , secure, expires, discard, None, None, rest)

        if cookie_storage.__class__.__name__ == 'str':
            cj = LWPCookieJar(cookie_storage)
            toPyCookieJar(self.cookie_jar, cj)
            cj.save()
        elif cookie_storage.__class__.__name__.endswith('CookieJar'):
            toPyCookieJar(self.cookie_jar, cookie_storage)
        else:
            raise ValueError, 'unsupported cookie_storage type.'


    def wait_for_confirm(self, confirm=True, callback=None):
        """Statement that tells GRobot how to deal with javascript confirm().

        @param confirm: A bollean that confirm.
        @param callable: A callable that returns a boolean for confirmation.
        """

        self._robot._confirm_expected = (confirm, callback)
        self._robot.wait_for(lambda: self._robot._confirm_expected is None)
        return self.popup_messages


    def wait_for_text(self, text, time_for_stop=None):
        """Waits until given text appear on main frame.

        @param text: The text to wait for.
        @return:
        """

        logger.debug("Wait for text %s" % text)

        self.wait_for(lambda: text in self.content,
                      "Can\'t find '%s' in current frame" % text, time_for_stop=time_for_stop)

        return self.wait_for_page_loaded()

    def wait_for_xpath(self, expression, time_for_stop=None):
        self.wait_for(lambda: XPath(self.content).execute(expression),
                      "Can't find xpath=%s in current frame" % expression, time_for_stop=time_for_stop)
        return self.wait_for_page_loaded()


    def wait_for_selector(self, selector):
        """Waits until selector match an element on the frame.

        @param selector: The selector to wait for.
        """
        self.wait_for(lambda: self.exists(selector),
                      'Can\'t find element matching "%s"' % selector)

    def wait_for_page_loaded(self, time_for_stop=None):
        """Waits until page is loaded, assumed that a page as been requested.

        """
        return self.wait_for(lambda: self._loaded,
                             'Unable to load requested page', time_for_stop=time_for_stop)

    def wait_for(self, condition, timeout_message='', time_for_stop=None):
        """Waits until condition is True.

        @param condition: A callable that returns the condition.
        @param timeout_message: The exception message on timeout.-1 means never timeout.
        """

        if self._loaded:
            time_for_stop = time_for_stop or self.operate_timeout
        else:
            time_for_stop = time_for_stop or self.loading_timeout

        started_at = time.time()
        while not condition():
            if time_for_stop != -1 and time.time() > (started_at + time_for_stop):
                if self._loaded:
                    raise OperateTimeout, timeout_message
                else:
                    # raise LoadingTimeout, timeout_message
                    self.trigger_action('Stop') #QWebPage::Stop
                    self._loaded = True
                    logger.warning("Page loading timeout.Force to stop the page")
                    break

            gevent.sleep(2)

    def wait_for_alert(self):
        """Waits for main frame alert().
        """
        self.wait_for(lambda: self._alert is not None,
                      'User has not been alerted.')
        msg, self._alert = self._alert, None
        return msg

    def _release_last_resources(self):
        """Releases last loaded resources.

        :return: The released resources.
        """
        last_resources, self.http_resources = self.http_resources[:], []
        return last_resources


    def _page_loaded(self, success):
        if self.develop and self.display:
            if self.inspector is None:
                self.inspector = QWebInspector()

            self.inspector.setPage(self.page)
            self.inspector.show()

        scripts = [
            'atoms.js',
            'htmlutils.js',
        ]

        if self.jquery_namespace:
            scripts.append('jquery-1.9.1.min.js', )

        for script in scripts:
            self.evaluate_js_file(os.path.dirname(__file__) + '/../javascripts/' + script)

        if self.jquery_namespace:
            self.evaluate(u"%s=jQuery.noConflict();" % self.jquery_namespace)

        self._loaded = True
        # self.cache.clear()
        logger.debug("Page load finished")

    def _page_load_started(self):
        logger.debug("Start load page")

        self._loaded = False

    def _unsupported_content(self, reply):
        """Adds an HttpResource object to http_resources with unsupported
        content.

        @param reply: The QNetworkReply object.
        """

        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute):
            self.http_resources.append(HttpResource(reply, self.cache,
                                                    reply.readAll()))

    def _link_clicked(self, href):
        """Contorl the page link clicked event,forbid open new window.

        @param href: The href attribute of a tag.
        """

        self.main_frame.load(href)

    def _request_ended(self, reply):
        """Adds an HttpResource object to http_resources.

        @param reply: The QNetworkReply object.
        """

        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute):
            self.http_resources.append(HttpResource(reply, self.cache))

    def _authenticate(self, mix, authenticator):
        """Called back on basic / proxy http auth.

        @param mix: The QNetworkReply or QNetworkProxy object.
        @param authenticator: The QAuthenticator object.
        """
        if self._auth_attempt == 0:
            username, password = self._auth
            authenticator.setUser(username)
            authenticator.setPassword(password)
            self._auth_attempt += 1

    def _on_manager_ssl_errors(self, reply, errors):
        """Ingore all the ssl error

        @param reply:
        @param errors:
        """
        url = unicode(reply.url().toString())
        if self.ignore_ssl_errors:
            reply.ignoreSslErrors()
        else:
            logger.warning('SSL certificate error: %s' % url)


    def _exit(self):
        """Destroy the Qt main event loop.

        """
        GRobot.exit_lock.acquire()
        if self.inspector:
            self.inspector.close()
            sip.delete(self.inspector)

        if self.display:
            self.webview.close()
            sip.delete(self.webview)

        if self.page and not sip.isdeleted(self.page):
            sip.delete(self.page)

        GRobot._liveRobot -= 1

        if GRobot._liveRobot == 0 and GRobot._loop is not None:

            GRobot._loop.stop()
            GRobot._loop = None
            GRobot._app = None
            if hasattr(self, 'xvfb'):
                GRobot.xvfb.terminate()
        GRobot.exit_lock.release()
