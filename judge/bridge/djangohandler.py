import logging
import SocketServer
import json
import struct

logger = logging.getLogger('judge.bridge')
size_pack = struct.Struct('!I')


class DjangoHandler(SocketServer.StreamRequestHandler):
    def __init__(self, *args, **kwargs):
        SocketServer.StreamRequestHandler.__init__(self, *args, **kwargs)

        self.handlers = {
            'submission-request': self.on_submission,
            'terminate-submission': self.on_termination,
        }

    def handle(self):
        input = self.rfile.read(4)
        if not input:
            return
        length = size_pack.unpack(input)[0]
        input = self.rfile.read(length)
        if not input:
            return
        self.rfile.close()
        input = input.decode('zlib')
        packet = json.loads(input)
        result = self.packet(packet)
        output = json.dumps(result, separators=(',', ':'))
        output = output.encode('zlib')
        self.wfile.write(size_pack.pack(len(output)))
        self.wfile.write(output)
        self.wfile.close()

    def packet(self, data):
        try:
            return self.handlers.get(data.get('name', None), lambda data: None)(data)
        except:
            logger.exception('Error in packet handling (Django-facing)')
            return {"name": "bad-request"}

    def on_submission(self, data):
        id = data['submission-id']
        problem = data['problem-id']
        language = data['language']
        source = data['source']
        self.server.judges.judge(id, problem, language, source)
        return {'name': 'submission-received', 'submission-id': id}

    def on_termination(self, data):
        try:
            self.server.judges.abort(data['submission-id'])
        except KeyError:
            return {"name": "bad-request"}

    def on_malformed(self, packet):
        logger.error('Malformed packet: %s', packet)
