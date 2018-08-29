import time

start_time = None
def game_time(is_real_time, bot_start=None):
    global start_time
    
    if bot_start != None:
        start_time = bot_start
        return
        
    t = time.time() - start_time
    
    if is_real_time:
        return t
    else:
        return 15*t
        
