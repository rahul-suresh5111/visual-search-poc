import io
from typing import Tuple, Optional
from PIL import Image
from backend.config import Config

class ImageProcessor:
    """Process and validate uploaded images"""
    
    @staticmethod
    def validate_image(uploaded_file) -> Tuple[bool, Optional[str]]:
        """Validate uploaded image file"""
        # Check file size
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > Config.MAX_FILE_SIZE_MB:
            return False, f"File size exceeds {Config.MAX_FILE_SIZE_MB}MB limit"
        
        # Check file extension
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_extension not in Config.ALLOWED_EXTENSIONS:
            return False, f"File type not allowed. Allowed types: {', '.join(Config.ALLOWED_EXTENSIONS)}"
        
        # Try to open the image
        try:
            image = Image.open(uploaded_file)
            image.verify()
            return True, None
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    @staticmethod
    def process_image(uploaded_file, max_size: Tuple[int, int] = (1920, 1920)) -> bytes:
        """Process image: resize if needed and convert to bytes"""
        # Open the image
        image = Image.open(uploaded_file)
        
        # Convert RGBA to RGB if necessary
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        
        # Resize if larger than max_size
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue()
    @staticmethod
    def get_image_metadata(uploaded_file) -> dict:
        """Extract metadata from uploaded image"""
        try:
            uploaded_file.seek(0)  # Reset file position
            image = Image.open(uploaded_file)
            
            metadata = {
                'format': str(image.format) if image.format else 'Unknown',
                'mode': str(image.mode) if image.mode else 'Unknown',
                'size': f"{image.size[0]}x{image.size[1]}",
                'width': str(image.size[0]),
                'height': str(image.size[1])
            }
            
            return metadata
            
        except Exception as e:
            return {'error': str(e)}
    
    