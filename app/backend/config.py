import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Azure settings"""
    
    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    DATABRICKS_HOST = os.getenv('DATABRICKS_HOST')
    DATABRICKS_TOKEN = os.getenv('DATABRICKS_TOKEN')
    DATABRICKS_JOB_ID = int(os.getenv('DATABRICKS_JOB_ID', '0'))
    AZURE_STORAGE_ACCOUNT = os.getenv('AZURE_STORAGE_ACCOUNT', 'cxdldevsea')
    AZURE_STORAGE_CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'image-data')
    AZURE_SAS_TOKEN = os.getenv('AZURE_SAS_TOKEN')

    
    # Application Configuration
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '10'))
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'avif', 'bmp', 'gif', 'tiff', 'tif', 
        'jfif', 'ico', 'heic', 'heif', 'raw', 'svg', 'psd', 'eps', 'indd', 'cdr', 'pdf'}
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("Missing AZURE_STORAGE_CONNECTION_STRING in .env file")
        return True