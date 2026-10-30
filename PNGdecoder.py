import os
import machine
import gc
import time

# ═══════════════════════════════════════════
# ⚠️ اطلاعات ورود خود را اینجا وارد کنید ⚠️
# ═══════════════════════════════════════════
STUDENT_ID = "4031219515"   # شماره دانشجویی خود را اینجا بگذارید
# ⚠️⚠️ هش MD5 واقعی پسورد خود را اینجا بگذارید ⚠️⚠️
PASSWORD_HASH = "f5ca68d79edc1e98383df58b8ebfb2c2" 
# ═══════════════════════════════════════════

state = "NET"
try:
    with open("state.txt", "r") as f:
        state = f.read().strip()
except:
    pass

print("Current State:", state)
gc.collect()

if state == "NET":
    print("--- PHASE 1: NETWORK ---")
    import network
    import urequests
    import re
    
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    if not wifi.isconnected():
        wifi.connect("HAKIM-WIFI", "")
        timeout = 10
        while not wifi.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    
    if wifi.isconnected():
        print("✅ WiFi Connected!")
        gc.collect()
        try:
            dummy = bytearray(20000)
            del dummy
            gc.collect()
        except: pass
        
        print("Waiting 2 seconds...")
        time.sleep(2)
        
        rand2 = None
        cookie = ""
        
        for attempt in range(3):
            try:
                print(f"Fetching rand2 (Attempt {attempt+1})...")
                headers_login = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                r_login = urequests.get("https://pooya.hsu.ac.ir/gateway/PuyaAuthenticate.php", headers=headers_login)
                
                for key, val in r_login.headers.items():
                    if key.lower() == "set-cookie":
                        cookie = val.split(";")[0]
                        break
                
                buffer = b""
                while True:
                    chunk = r_login.raw.read(512)
                    if not chunk:
                        break
                    buffer += chunk
                    match = re.search(rb'id=[\'"]rand2[\'"][^>]*value=[\'"]([^\'"]+)', buffer)
                    if match:
                        rand2 = match.group(1).decode()
                        break
                    if len(buffer) > 1024:
                        buffer = buffer[-100:]
                
                r_login.close()
                del r_login
                del buffer
                gc.collect()
                
                if rand2: break
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1} failed: {e}")
                time.sleep(2)
            
        if rand2:
            print("✅ rand2 Found.")
            print("Downloading Captcha (HTTP)...")
            url = f"http://pooya.hsu.ac.ir/gateway/SecurityImage/ShowSecurityImage.php?rand=1441993486&rand2={rand2}"
            headers_img = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Cookie": cookie,
                "Referer": "https://pooya.hsu.ac.ir/gateway/PuyaAuthenticate.php"
            }
            
            try:
                r_img = urequests.get(url, headers=headers_img)
                img_data = r_img.content
                r_img.close()
                del r_img
                
                if len(img_data) > 0:
                    with open("captcha.png", "wb") as f:
                        f.write(img_data)
                    print("✅ Captcha downloaded. Size:", len(img_data))
                    
                    with open("session.txt", "w") as f:
                        f.write(rand2 + "\n" + cookie)
                    with open("state.txt", "w") as f:
                        f.write("UI")
                    print("Rebooting...")
                    time.sleep(1)
                    machine.reset()
            except Exception as e:
                print("❌ Image Download Error:", e)

elif state == "UI":
    print("--- PHASE 2: UI & RENDER ---")
    from machine import Pin, SPI
    from ili9341 import Display
    from xpt2046 import Touch
    from PNGdecoder import png
    import framebuf
    
    try:
        dummy = bytearray(25000)
        del dummy
        gc.collect()
    except: pass
    
    spi = SPI(1, baudrate=10000000, sck=Pin(14), mosi=Pin(13))
    display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(22), width=240, height=320, rotation=270)
    Pin(21, Pin.OUT).on()
    
    def color(r, g, b): return ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)
    BLACK = color(0,0,0); WHITE = color(255,255,255); BLUE = color(0,100,255)
    GRAY = color(80,80,80); GREEN = color(0,200,0); RED = color(200,0,0); DARK = color(30,30,30)
    LIGHTGRAY = color(150, 150, 150)
    
    def draw_text(disp, x, y, text, fg, bg, scale=1):
        if not text: return
        w = len(text) * 8; h = 8
        buf = bytearray(w * h * 2)
        fb = framebuf.FrameBuffer(buf, w, h, framebuf.RGB565)
        fb.fill(bg); fb.text(text, 0, 0, fg)
        for yy in range(h):
            for xx in range(w):
                idx = (yy * w + xx) * 2
                c = (buf[idx+1] << 8) | buf[idx]
                disp.fill_rectangle(x + xx*scale, y + yy*scale, scale, scale, c)
    
    captcha_input = ""
    NUM_KEYS = [['1','2','3'],['4','5','6'],['7','8','9'],['DEL','0','OK']]
    KEY_Y = 155; KEY_W = 74; KEY_H = 34; GAP = 2
    INPUT_Y = 110; INPUT_W = 165; REFRESH_X = 175; REFRESH_W = 60

    def draw_input_box():
        display.fill_rectangle(5, INPUT_Y, INPUT_W, 40, WHITE)
        draw_text(display, 10, INPUT_Y + 15, captcha_input[-10:], BLACK, WHITE, scale=2)
    
    def draw_refresh_btn():
        display.fill_rectangle(REFRESH_X, INPUT_Y, REFRESH_W, 40, RED)
        draw_text(display, REFRESH_X + 6, INPUT_Y + 15, "REFRESH", WHITE, RED, scale=1)

    def draw_single_key(row, col, is_pressed=False):
        x = col * (KEY_W + GAP) + 4; y = KEY_Y + (row * (KEY_H + GAP)) + GAP
        key = NUM_KEYS[row][col]
        bg = GRAY
        if key == 'OK': bg = GREEN
        elif key == 'DEL': bg = RED
        if is_pressed: bg = LIGHTGRAY
        display.fill_rectangle(x, y, KEY_W, KEY_H, bg)
        tw = len(key) * 8; tx = x + (KEY_W - tw) // 2; ty = y + (KEY_H - 8) // 2
        draw_text(display, tx, ty, key, WHITE, bg, scale=1)

    def draw_keyboard():
        display.fill_rectangle(0, KEY_Y, 239, 165, BLACK)
        for r in range(4):
            for c in range(3):
                draw_single_key(r, c)

    display.fill_rectangle(0, 0, 239, 319, BLACK)
    draw_text(display, 85, 5, "ENTER CAPTCHA", WHITE, BLACK, scale=1)
    draw_input_box()
    draw_refresh_btn()
    draw_keyboard()
    
    def draw_pixel(x, y, c):
        r = (c >> 16) & 0xFF; g = (c >> 8) & 0xFF; b = c & 0xFF
        display.draw_pixel(x, y, ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3))
    try:
        png('captcha.png', callback=draw_pixel).render(5, 25)
    except Exception as e:
        print("❌ Render Error:", e)
    
    touch_spi = SPI(2, baudrate=1000000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))
    
    def touched(raw_x, raw_y):
        global captcha_input
        if raw_x < 20: raw_x = 20
        if raw_x > 207: raw_x = 207
        if raw_y < 20: raw_y = 20
        if raw_y > 303: raw_y = 303
        sx = int((raw_x - 20) * 239 / (207 - 20))
        sy = int((303 - raw_y) * 319 / (303 - 20))
    
        if (REFRESH_X <= sx <= REFRESH_X + REFRESH_W) and (INPUT_Y <= sy <= INPUT_Y + 40):
            with open("state.txt", "w") as f: f.write("NET")
            time.sleep(0.5); machine.reset(); return
    
        if sy >= KEY_Y:
            col = int((sx - 4) // (KEY_W + GAP))
            row = int((sy - KEY_Y - GAP) // (KEY_H + GAP))
            if 0 <= row < 4 and 0 <= col < 3:
                key = NUM_KEYS[row][col]
                draw_single_key(row, col, is_pressed=True)
                time.sleep(0.03)
                if key == 'DEL': captcha_input = captcha_input[:-1]
                elif key == 'OK':
                    if captcha_input:
                        with open("login.txt", "w") as f: f.write(captcha_input)
                        with open("state.txt", "w") as f: f.write("LOGIN")
                        time.sleep(0.5); machine.reset()
                else:
                    if len(captcha_input) < 10: captcha_input += key
                draw_single_key(row, col, is_pressed=False)
                draw_input_box()

    touch = Touch(touch_spi, cs=Pin(33), int_pin=Pin(36), int_handler=touched)
    print("System Ready.")
    while True:
        touch.get_touch(); time.sleep(0.05)

elif state == "LOGIN":
    print("--- PHASE 3: LOGIN ---")
    import network
    import urequests
    
    with open("session.txt", "r") as f:
        session_data = f.read().split("\n")
        rand2 = session_data[0]
        cookie = session_data[1]
        
    with open("login.txt", "r") as f:
        captcha = f.read().strip()
        
    print("User ID:", STUDENT_ID)
    print("Captcha:", captcha)
    
    def url_encode(s):
        safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
        return "".join(c if c in safe else "%%%02X" % ord(c) for c in s)
    
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect("HAKIM-WIFI", "")
    while not wifi.isconnected():
        time.sleep(1)
    print("✅ WiFi Connected!")
    
    LOGIN_URL = "https://pooya.hsu.ac.ir/gateway/UserInterim.php"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://pooya.hsu.ac.ir/gateway/PuyaAuthenticate.php",
        "Origin": "https://pooya.hsu.ac.ir",
        "Connection": "keep-alive"
    }
    
    post_data = f"UserID={url_encode(STUDENT_ID)}&UserPassword={PASSWORD_HASH}&DummyVar=&pswdStatus=Strong&mysecpngco={url_encode(captcha)}&rand2={url_encode(rand2)}"
    
    print("Sending POST request...")
    try:
        r = urequests.post(LOGIN_URL, data=post_data, headers=headers)
        print("✅ Server Responded! Status:", r.status_code)
        response_text = r.text
        
        if "زمان ورود کد امنیتی" in response_text:
            print("❌ Error: Captcha Expired! You took too long to type.")
        elif "browser error" in response_text.lower():
            print("❌ Error: Browser Error (Check Password Hash).")
        elif "کد امنیتی" in response_text or "اشتباه" in response_text:
            print("❌ Error: Wrong Captcha or Password.")
        elif "logout" in response_text.lower() or "پرتال دانشجویی" in response_text:
            print("🎉 LOGIN SUCCESSFUL! You are in!")
        else:
            print("⚠️ Unknown response.")
            
        r.close()
    except Exception as e:
        print("❌ Login Error:", e)
        
    for file in ["state.txt", "session.txt", "login.txt"]:
        try: os.remove(file)
        except: pass