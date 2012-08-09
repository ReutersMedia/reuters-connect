import urllib2
import urllib
import time

from xml.etree.ElementTree import ElementTree, fromstring

AUTH_URL = "https://commerce.reuters.com/rmd/rest/xml/"
SERVICE_URL = "http://rmb.reuters.com/rmd/rest/xml/"

       


class AuthTokenMemoryCache:
    def __init__(self, renew_secs=3600):
        self.token = None
        self.exp = 0
        self.renew_secs = renew_secs
    def get(self):
        if time.time() > self.exp:
            return None
        return self.t
    def set(self,t):
        self.t=t
        self.exp = time.time() + self.renew_secs


class AuthTokenFileCache:
    """
    Cache the auth token on the local disk
    """
    def __init__(self, path, renew_secs=3600):
        self.mem_cache = AuthTokenMemoryCache(renew_secs)
        self.path = None
    def get(self):
        t = self.mem_cache.get()
        if t == None:
            try:
                d = open(path,"r").read()
            except IOError, err:
                if err.errno == 2:
                    # doesn't exist
                    return None
                raise
            tok,exp = eval(d)
            self.mem_cache.token = tok
            self.mem_cache.exp = exp
            # try again
            t = self.mem_cache.get()
        return t
    def set(self, t):
        self.mem_cache.set(t)
        open(self.path,"w").write( repr( (t, self.mem_cache.exp) ) )
    
        

class Connection:

    METHODS = ["channels","items","item","search"]

    def __init__(self,
                 username,
                 password,
                 proxy=None,
                 timeout=10,
                 auth_cache=AuthTokenMemoryCache()):
        self.auth_cache = auth_cache
        self.username = username
        self.password = password
        self.timeout = timeout

        def make_f(method):
            def m_f(self, **args):
                return self._call(method,**args)
            return m_f

        for m in self.METHODS:
            f = make_f(m)
            f.__name__ = m
            f.__doc__ = "call method %s, returns XML tree" % m
            setattr(Connection,f.__name__,f)

        h = urllib2.ProxyHandler(proxy)
        self.client = urllib2.build_opener(h)

    def login(self):
        # special method, uses object attributes
        return self._call('login', username=self.username, password=self.password)

    def get_auth_token(self):
        if self.auth_cache != None:
            t = self.auth_cache.get()
            if t != None:
                return t
        # no token, get a new one
        tree = self.login()
        if tree.tag == 'authToken':
            t = tree.text
        else:
            raise Exception('unable to authorize with Reuters Connect service')
        if self.auth_cache != None:
            self.auth_cache.set(t)
        return t

    def _call(self, method, **args):
        if method == 'login':
            root_url = AUTH_URL
        else:
            root_url = SERVICE_URL
            args['token'] = self.get_auth_token()
        # if timeout in args, pull and use it for timeout
        timeout = args.pop('timeout',self.timeout)
        url = root_url + method + '?' + urllib.urlencode(args)
        resp = self.client.open(url, timeout=timeout)
        rawd = resp.read()
        return fromstring(rawd) 

