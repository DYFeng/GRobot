import SOAPpy

class GRobotTestDriver(object):

    def __init__(self, *args, **kwargs):
        self.session_id = None

        if 'server' in kwargs:
            server = kwargs['server']
            del kwargs['server']
        else:
            server = "http://127.0.0.1:8888"

        self.grobot_server = SOAPpy.SOAPProxy(server)

        self.session_id = self.grobot_server.create_robot(*args, **kwargs)

    def __getattr__(self, item):
        return lambda *args, **kwargs: self.grobot_server.method(item, session_id=self.session_id, *args, **kwargs)

    def exit(self):
        self.grobot_server.destroy_robot(self.session_id)

