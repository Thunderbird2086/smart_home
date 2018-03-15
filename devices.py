import smart_switch

def load(listener, poller):
    smart_switch.load(listener, poller)

    smart_switch.notify(listener.ssock)
