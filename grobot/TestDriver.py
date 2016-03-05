import SOAPpy


class GRobotTestDriver(object):
    def __init__(self, *args, **kwargs):
        self.session_id = None

        self.grobot_server = SOAPpy.SOAPProxy(kwargs.pop('server', 'http://127.0.0.1:8888'))

        self.session_id = self.grobot_server.create_robot(*args, **kwargs)

    def __getattr__(self, item):
        return lambda *args, **kwargs: self.grobot_server.method(item, session_id=self.session_id, *args, **kwargs)

    def exit(self):
        self.grobot_server.destroy_robot(self.session_id)
