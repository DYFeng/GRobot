#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
import logging

from grobot import GRobot, confirm, prompt
from app import app
import gevent
from gevent.wsgi import WSGIServer
from PyQt4.QtWebKit import *
from PyQt4.QtCore import *

PORT = 5000

base_url = 'http://localhost:%s/' % PORT



class GRobotTest(unittest.TestCase):
    port = PORT
    display = False
    develop = True
    log_level = logging.DEBUG


    @classmethod
    def setUpClass(cls):
        http_server = WSGIServer(('', PORT), app, log=None)
        cls.server = gevent.spawn(http_server.serve_forever)
        gevent.sleep(3)

    @classmethod
    def tearDownClass(cls):
        cls.server.kill()

    def tearDown(self):
        self.robot = None

    def setUp(self):
        self.robot = GRobot(
            display=GRobotGeneralTest.display,
            develop=GRobotGeneralTest.develop,
            log_level=GRobotGeneralTest.log_level
        )


class GRobotGeneralTest(GRobotTest):

    def test_open(self):
        self.robot.open(base_url)
        self.assertEqual(self.robot.url, base_url)
        self.assertTrue("Test page" in self.robot.content)


    def test_evaluate(self):
        self.robot.open(base_url)
        self.assertEqual(self.robot.evaluate("x='ghost'; x;"), 'ghost')

    def test_extra_resource_binaries(self):
        self.robot.open("%simage" % base_url)
        self.assertEqual(self.robot.http_resources[1].content.__class__.__name__,
                         'QByteArray')

    def test_settimeout(self):
        self.robot.open("%ssettimeout" % base_url)
        result = self.robot.evaluate("document.getElementById('result').innerHTML")
        self.assertEqual(result, 'Bad')
        gevent.sleep(4)
        result = self.robot.evaluate("document.getElementById('result').innerHTML")
        self.assertEqual(result, 'Good')

    def test_wait_for_timeout(self):
        self.robot.open("%s" % base_url)
        self.assertRaises(Exception, self.robot.wait_for_text, "undefined")


    def test_global_exists(self):
        self.robot.open("%s" % base_url)
        self.assertTrue(self.robot.global_exists('myGlobal'))

    def test_cookies(self):
        self.robot.open("%scookie" % base_url)
        self.assertEqual(len(self.robot.cookies), 1)


    def test_delete_cookies(self):
        self.robot.open("%scookie" % base_url)
        self.robot.delete_cookies()
        self.assertEqual(len(self.robot.cookies), 0)

    def test_save_load_cookies(self):
        self.robot.delete_cookies()
        self.robot.open("%sset/cookie" % base_url)
        self.robot.save_cookies('testcookie.txt')
        self.robot.delete_cookies()
        self.robot.load_cookies('testcookie.txt')
        self.robot.open("%sget/cookie" % base_url)
        self.assertTrue('OK' in self.robot.content)
        os.remove('testcookie.txt')

    # def test_capture_to(self):
    #     self.robot.open(base_url)
    #     self.robot.capture_to('test.png')
    #     self.assertTrue(os.path.isfile('test.png'))
    #     os.remove('test.png')

    # def test_region_for_selector(self):
    #     self.robot.open(base_url)
    #     x1, y1, x2, y2 = self.robot.region_for_selector('h1')
    #     self.assertEqual(x1, 8)
    #     self.assertEqual(y1, 21)
    #     self.assertEqual(x2, 791)

    def test_capture_selector_to(self):
        self.robot.open(base_url)
        files = self.robot.capture_to('test.png', selector='h1')
        for f in files:
            self.assertTrue(os.path.isfile(f))
            os.remove(f)

    def test_basic_http_auth_success(self):
        self.robot.open("%sbasic-auth" % base_url,
                        auth=('admin', 'secret'))
        self.assertIn('successfully authenticated', self.robot.content)


    def test_basic_http_auth_error(self):
        self.robot.open("%sbasic-auth" % base_url,
                        auth=('admin', 'wrongsecret'))
        self.assertIn('Could not verify your access level for that URL.', self.robot.content)


    def test_unsupported_content(self):
        self.robot.open("%ssend-file" % base_url)
        foo = open(os.path.join(os.path.dirname(__file__), 'static',
                                'foo.tar.gz'), 'r').read(1024)
        self.assertEqual(self.robot.http_resources[0].content, foo)

    def test_url_with_hash(self):
        self.robot.open("%surl-hash" % base_url)
        self.assertIsNotNone(self.robot.content)
        self.assertTrue("Test page" in self.robot.content)


    def test_url_with_hash_header(self):
        self.robot.open("%surl-hash-header" % base_url)
        self.assertTrue("Welcome" in self.robot.content)


    def test_wait_for_selector(self):
        self.robot.open("%smootools" % base_url)
        self.robot.selenium("click", "id=button")
        self.robot.wait_for_selector("#list li:nth-child(2)")

        self.assertEqual(self.robot.http_resources[-1].url, "%sitems.json" % base_url)

    def test_wait_for_text(self):
        self.robot.open("%smootools" % base_url)
        self.robot.selenium("click", "id=button")
        self.robot.wait_for_text("second item")
        self.assertEqual(self.robot.http_resources[-1].url, "%sitems.json" % base_url)

    # def test_page_with_no_cache_headers(self):
    #     self.robot.open("%sno-cache" % base_url)
    #     self.assertIsNotNone(page.content)
    #     self.assertIn("cache for me", page.content)

    # def test_http_status(self):
    #     self.robot.open("%sprotected" % base_url)
    #     self.assertEqual(page.http_status, 403)
    #     self.robot.open("%s404" % base_url)
    #     self.assertEqual(page.http_status, 404)


    # def test_external_api(self):
    #     self.robot.open("%smootools" % base_url)
    #     resources = self.robot.http_resources[:]
    #     self.assertEqual(len(resources), 2)
    #     self.assertEqual(type(self.robot.evaluate("document.id('list')")),
    #                      dict)

    # def test_extra_resource_content(self):
    #     self.robot.open("%smootools" % base_url)
    #     self.assertIn(u'MooTools: the javascript framework',
    #                   self.robot.http_resources[1].content)



class GrobotNativeTest(GRobotTest):

    # def test_postion(self):
    #     self.robot.open(base_url)
    #
    #     self.robot.set_page_center(1000,1000)
    #     # print self.robot.postions_from_selector("xpath=//div[@id='middle']")
    #     gevent.sleep(100000000)

    def test_click_link(self):
        self.robot.open("%s" % base_url)
        self.robot.click('xpath=//a', expect_loading=True)
        self.assertEqual(self.robot.url, "%sform" % base_url)


    def test_fill(self):
        self.robot.open("%sform" % base_url)

        values = {
            'text': 'Here is a sample text.',
            'email': 'my@awesome.email',
            'textarea': 'Here is a sample text.\nWith several lines.',
            'checkbox': True,
            'selectbox': 'two',
            "radio": "first choice"
        }

        self.robot.check('id=checkbox',True)
        value = self.robot.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)

        # self.robot.check('id=radio-first',True)
        # value = self.robot.evaluate(
        #     'document.getElementById("radio-first").checked')
        # self.assertEqual(value, True)
        #
        # self.robot.check('id=radio-second',False)
        # value = self.robot.evaluate(
        #     'document.getElementById("radio-second").checked')
        # self.assertEqual(value, False)

        self.robot.select('id=selectbox','value=one')
        value = self.robot.evaluate(
            'document.getElementById("selectbox").value')
        self.assertEqual(value, 'one')

        self.robot.select('id=selectbox','Two')
        value = self.robot.evaluate(
            'document.getElementById("selectbox").value')
        self.assertEqual(value, 'two')

        self.robot.select('id=long_selectbox','30')
        value = self.robot.evaluate(
            'document.getElementById("long_selectbox").value')
        self.assertEqual(value, '30')

        self.robot.select('id=multiple_selectbox','one')
        self.robot.select('id=multiple_selectbox','four')
        self.robot.select('id=multiple_selectbox','three',False)

        value = self.robot.evaluate(
        """
        var select_box=document.getElementById("multiple_selectbox");
          function getSelectValues(select) {
          var result = [];
          var options = select && select.options;
          var opt;

          for (var i=0, iLen=options.length; i<iLen; i++) {
            opt = options[i];

            if (opt.selected) {
              result.push(opt.value || opt.text);
            }
          }
          return result;
        }
        getSelectValues(select_box)
        """)
        self.assertEqual(value, ['one','four'])



class GRobotSeleniumTest(GRobotTest):


    def test_fill(self):
        self.robot.open("%sform" % base_url)
        values = {
            'text': 'Here is a sample text.',
            'email': 'my@awesome.email',
            'textarea': 'Here is a sample text.\nWith several lines.',
            'checkbox': True,
            'selectbox': 'two',
            "radio": "first choice"
        }

        self.robot.seleniumChain([
            ("type", "id=text", 'Here is a sample text.'),
            ("type", "id=email", 'my@awesome.email'),
            ("type", "id=textarea", 'Here is a sample text.\nWith several lines.'),
            ("check", "id=checkbox"),
            ("select", "id=selectbox", 'label=two'),
            ("click", "id=radio-first"),
        ])

        for field in ['text', 'email', 'textarea', 'selectbox']:
            value = self.robot.evaluate('document.getElementById("%s").value' % field)
            self.assertEqual(value, values[field])
        value = self.robot.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)
        value = self.robot.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value = self.robot.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)





    def test_form_submission(self):
        self.robot.open("%sform" % base_url)

        self.robot.seleniumChain([('type', 'id=contact-form', 'Here is a sample text.'),
                                  ('click', "xpath=//input[@type='submit']"),
                                 ], expect_loading=True)

        self.assertIn('form successfully posted', self.robot.content)



    # def test_resource_headers(self):
    #     self.robot.open(base_url)
    #     self.assertEqual(page.headers['Content-Type'], 'text/html; charset=utf-8')


    def test_click_link(self):
        self.robot.open("%s" % base_url)
        self.robot.selenium('click', 'xpath=//a', expect_loading=True)
        self.assertEqual(self.robot.url, "%sform" % base_url)


    def test_wait_for_alert(self):
        self.robot.open("%salert" % base_url)
        self.robot.selenium('click', 'id=alert-button')
        msg = self.robot.wait_for_alert()
        self.assertEqual(msg, 'this is an alert')

    def test_confirm(self):
        self.robot.open("%salert" % base_url)
        with confirm(self.robot):
            self.robot.selenium('click', 'id=confirm-button')
        msg = self.robot.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_no_confirm(self):
        self.robot.open("%salert" % base_url)
        with confirm(self.robot, False):
            self.robot.selenium('click', 'id=confirm-button')
        msg = self.robot.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_confirm_callback(self):
        self.robot.open("%salert" % base_url)
        with confirm(self.robot, callback=lambda: False):
            self.robot.selenium('click', 'id=confirm-button')
        msg = self.robot.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_prompt(self):
        self.robot.open("%salert" % base_url)
        with prompt(self.robot, 'my value'):
            self.robot.selenium('click', 'id=prompt-button')
        value = self.robot.evaluate('promptValue')
        self.assertEqual(value, 'my value')


    def test_prompt_callback(self):
        self.robot.open("%salert" % base_url)
        with prompt(self.robot, callback=lambda: 'another value'):
            self.robot.selenium('click', 'id=prompt-button')
        value = self.robot.evaluate('promptValue')
        self.assertEqual(value, 'another value')

    def test_popup_messages_collection(self):
        self.robot.open("%salert" % base_url)
        def _test():
            self.assertIn('this is a confirm', self.robot.popup_messages)
            return True
        with confirm(self.robot, True, callback=_test):
            self.robot.selenium('click', 'id=confirm-button')

        self.robot.wait_for_alert()

        with prompt(self.robot, confirm=False):
            self.robot.selenium('click', 'id=prompt-button')

        self.assertIn('Prompt ?', self.robot.popup_messages)

        self.robot.selenium('click', 'id=alert-button')

        self.assertIn('this is an alert', self.robot.popup_messages)

    def test_prompt_default_value_true(self):
        self.robot.open("%salert" % base_url, default_popup_response=True)
        self.robot.selenium('click', 'id=confirm-button')
        msg = self.robot.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_prompt_default_value_false(self):
        self.robot.open("%salert" % base_url, default_popup_response=False)
        self.robot.selenium('click', 'id=confirm-button')
        msg = self.robot.wait_for_alert()
        self.assertEqual(msg, 'you denied!')




    def test_set_field_value_checkbox_true(self):
        self.robot.open("%sform" % base_url)
        self.robot.selenium('check', 'id=checkbox')
        value = self.robot.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)


    def test_set_field_value_checkbox_false(self):
        self.robot.open("%sform" % base_url)
        self.robot.selenium('uncheck', 'id=checkbox')
        value = self.robot.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, False)


    def test_set_field_value_checkbox_multiple(self):
        self.robot.open("%sform" % base_url)
        self.robot.selenium('check',
                            'id=multiple-checkbox-second')
        value = self.robot.evaluate(
            'document.getElementById("multiple-checkbox-first").checked')
        self.assertEqual(value, False)
        value = self.robot.evaluate(
            'document.getElementById("multiple-checkbox-second").checked')
        self.assertEqual(value, True)


    def test_set_field_value_email(self):
        expected = 'my@awesome.email'
        self.robot.open("%sform" % base_url)
        self.robot.selenium('type', 'id=email', expected)
        value = self.robot.evaluate('document.getElementById("email").value')
        self.assertEqual(value, expected)


    def test_set_field_value_text(self):
        expected = 'sample text'
        self.robot.open("%sform" % base_url)
        self.robot.selenium('type', 'name=text', expected)
        value = self.robot.evaluate('document.getElementById("text").value')
        self.assertEqual(value, expected)


    def test_set_field_value_radio(self):
        self.robot.open("%sform" % base_url)
        self.robot.selenium('click', 'id=radio-first')
        value = self.robot.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value = self.robot.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)


    def test_set_field_value_textarea(self):
        expected = 'sample text\nanother line'
        self.robot.open("%sform" % base_url)
        self.robot.selenium('type', 'name=textarea', expected)
        value = self.robot.evaluate('document.getElementById("textarea").value')
        self.assertEqual(value, expected)


    def test_set_simple_file_field(self):
        self.robot.open("%supload" % base_url)
        self.robot.set_file_input('id=simple-file', os.path.dirname(__file__) + '/static/blackhat.jpg')
        self.robot.selenium('click', "xpath=//input[@type='submit']"
            , expect_loading=True)

        file_path = os.path.join(
            os.path.dirname(__file__), 'uploaded_blackhat.jpg')
        self.assertTrue(os.path.isfile(file_path))
        os.remove(file_path)




if __name__ == '__main__':
    unittest.main()
