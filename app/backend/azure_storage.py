import os
import uuid
from datetime import datetime
from typing import Optional, Dict
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import streamlit as st

from backend.config import Config

class AzureStorageHandler:
    """Handler for Azure Blob Storage operations"""
    
    def __init__(self):
        self.connection_string = Config.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = Config.AZURE_STORAGE_CONTAINER_NAME
        self.blob_service_client = None
        self.container_client = None
        
    def connect(self) -> bool:
        """Establish connection to Azure Blob Storage"""
        try:
            if not self.connection_string:
                raise ValueError("Azure Storage connection string not configured")
            
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            self._ensure_container_exists()
            return True
            
        except Exception as e:
            st.error(f"Failed to connect to Azure Storage: {str(e)}")
            return False
    
    def _ensure_container_exists(self):
        """Ensure the storage container exists, create if not"""
        try:
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            self.container_client.get_container_properties()
            
        except ResourceNotFoundError:
            try:
                self.container_client = self.blob_service_client.create_container(
                    self.container_name,
                    public_access=None
                )
                print(f"Created container: {self.container_name}")
            except ResourceExistsError:
                pass
    
    def upload_image(self, file_data: bytes, file_name: str, metadata: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Upload an image to Azure Blob Storage"""
        try:
            # Use basic timestamp format without special characters
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            file_extension = os.path.splitext(file_name)[1]
            blob_name = f"{timestamp}_{unique_id}{file_extension}"
            
            st.info(f"Uploading as: {blob_name}")
            
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Clean metadata - ensure ASCII-safe strings
            clean_metadata = {
                'original_filename': file_name.encode('ascii', 'ignore').decode('ascii'),
                'upload_timestamp': timestamp,  # Use simple timestamp
                'source': 'visual_search_poc'
            }
            
            # Upload the blob WITHOUT metadata first to test
            blob_client.upload_blob(
                file_data,
                overwrite=True
                # Temporarily remove metadata parameter
            )
            
            st.success(f"Successfully uploaded: {blob_name}")
            return blob_client.url
            
        except Exception as e:
            st.error(f"Azure Upload Error: {type(e).__name__}")
            st.error(f"Details: {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            return None