from PIL import Image, ImageDraw, ImageFont
import os

def create_test_images():
    os.makedirs("test_data", exist_ok=True)
    
    # Create Portrait Side
    p_img = Image.new('RGB', (1000, 600), color=(240, 240, 240))
    d = ImageDraw.Draw(p_img)
    # Draw a "face" (MediaPipe might not detect a simple oval, but it's a start)
    # Actually, for MediaPipe to work, it needs a real face. 
    # Since I can't generate a real face, I'll rely on the fact that 
    # the user will use real photos. 
    # For testing the logic, I'll manually mock the 'portrait' side in the test script.
    d.text((50, 100), "姓名 姓名 性别 民族 出生 住址 公民身份号码 号码", fill=(0, 0, 0))
    p_img.save("test_data/portrait.jpg")
    
    # Create Emblem Side
    e_img = Image.new('RGB', (1000, 600), color=(200, 220, 255))
    d = ImageDraw.Draw(e_img)
    # Draw a large red circle for the emblem
    d.ellipse([400, 100, 600, 300], fill=(255, 0, 0))
    d.text((50, 400), "中华人民共和国 居民身份证 签发机关 有效期限 期限", fill=(0, 0, 0))
    e_img.save("test_data/emblem.jpg")
    
    print("Test images created in 'test_data' folder.")

if __name__ == "__main__":
    create_test_images()
