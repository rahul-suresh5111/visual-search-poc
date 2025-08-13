import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Azure settings"""
    
    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    AZURE_STORAGE_CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'product-images')
    
    # Application Configuration
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '10'))
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("Missing AZURE_STORAGE_CONNECTION_STRING in .env file")
        return True