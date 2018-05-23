from xmlrpc.server import SimpleXMLRPCServer

def set_level(value):
    return True

def main(port=54357):
    server = SimpleXMLRPCServer(('localhost', port))
    print('Listening on port {}...'.format(port))
    server.register_function(set_level, 'set_level')
    server.serve_forever()

if __name__=='__main__':
    main()