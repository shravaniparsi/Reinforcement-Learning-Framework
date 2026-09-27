"""Wait for observed request completion after SPA transitions, without interception."""
import time

class NetworkQuiet:
    def __init__(self,page):
        self.page=page
        self.active=set()
        self.last_change=time.monotonic()
        page.on('request',self.started)
        page.on('requestfinished',self.ended)
        page.on('requestfailed',self.ended)

    def started(self,request):
        self.active.add(request)
        self.last_change=time.monotonic()

    def ended(self,request):
        self.active.discard(request)
        self.last_change=time.monotonic()

    def wait(self,quiet_ms=500,timeout_ms=30000):
        start=time.monotonic()
        # Pump events for a new quiet interval even if an earlier lifecycle idle fired.
        quiet_start=max(start,self.last_change)
        while True:
            now=time.monotonic()
            quiet_start=max(quiet_start,self.last_change)
            if not self.active and (now-quiet_start)*1000>=quiet_ms:
                return {'wait_ms':(now-start)*1000,'pending':0}
            if (now-start)*1000>=timeout_ms:
                raise TimeoutError(f'Network did not settle; {len(self.active)} active requests')
            self.page.wait_for_timeout(25)
