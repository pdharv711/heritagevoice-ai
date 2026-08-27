import os
from PIL import Image, ImageDraw

def create_image(filename: str, width: int, height: int, color: str, text: str):
    # Create solid color image
    img = Image.new("RGB", (width, height), color=color)
    d = ImageDraw.Draw(img)
    
    # Draw simple centered rectangle representing a monument
    d.rectangle([width//4, height//4, width*3//4, height*3//4], outline="white", width=4)
    # Add text banner
    d.text((width//3, height//2), text, fill="white")
    
    # Save the image
    os.makedirs("../test_images", exist_ok=True)
    filepath = os.path.join("../test_images", filename)
    img.save(filepath)
    print(f"Created: {filepath} ({width}x{height})")

if __name__ == "__main__":
    print("Generating demo test images...")
    # Sizes carefully chosen so that (w + h) % 5 matches the catalog index
    # 0: taj_mahal (800 % 5 = 0)
    # 1: red_fort (801 % 5 = 1)
    # 2: sun_temple (802 % 5 = 2)
    # 3: hampi (803 % 5 = 3)
    # 4: qutub_minar (804 % 5 = 4)
    create_image("taj_mahal_test.jpg", 400, 400, "teal", "Taj Mahal Test Image")
    create_image("red_fort_test.jpg", 401, 400, "brown", "Red Fort Test Image")
    create_image("sun_temple_test.jpg", 402, 400, "orange", "Sun Temple Test Image")
    create_image("hampi_test.jpg", 403, 400, "gold", "Hampi Test Image")
    create_image("qutub_minar_test.jpg", 404, 400, "darkred", "Qutub Minar Test Image")
    print("Finished generating test images.")
