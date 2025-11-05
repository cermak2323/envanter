"""
Backblaze B2 Storage Service
Bu dosya Backblaze B2 ile dosya yükleme, indirme ve silme işlemlerini yönetir.
"""

import os
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from dotenv import load_dotenv
import hashlib
import logging

# Environment variables yükle
load_dotenv()

class B2StorageService:
    def __init__(self):
        # Render.com environment variable names
        self.application_key_id = os.getenv('B2_APPLICATION_KEY_ID') or os.getenv('B2_KEY_ID')
        self.application_key = os.getenv('B2_APPLICATION_KEY')
        self.bucket_name = os.getenv('B2_BUCKET_NAME')
        
        if not all([self.application_key_id, self.application_key, self.bucket_name]):
            raise ValueError("B2 credentials are not properly configured in .env file")
        
        # B2 API başlatma
        self.info = InMemoryAccountInfo()
        self.b2_api = B2Api(self.info)
        self.bucket = None
        
        # B2 authorize
        self._authorize()
    
    def _authorize(self):
        """B2 API ile yetkilendirme"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.b2_api.authorize_account("production", self.application_key_id, self.application_key)
                
                # Bucket'ı kontrol et, yoksa oluştur
                try:
                    self.bucket = self.b2_api.get_bucket_by_name(self.bucket_name)
                    logging.info(f"Successfully connected to existing B2 bucket: {self.bucket_name}")
                    return
                except Exception:
                    # Bucket yoksa oluştur
                    logging.info(f"Creating new B2 bucket: {self.bucket_name}")
                    self.bucket = self.b2_api.create_bucket(self.bucket_name, "allPrivate")
                    logging.info(f"Successfully created B2 bucket: {self.bucket_name}")
                    return
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"B2 authorization attempt {attempt + 1} failed, retrying: {e}")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logging.error(f"B2 authorization failed after {max_retries} attempts: {e}")
                    raise
    
    def upload_file(self, file_path, file_content, content_type='image/png'):
        """
        Dosyayı B2'ye yükle
        
        Args:
            file_path (str): B2'deki dosya yolu (örn: 'qr_codes/item_123.png')
            file_content (bytes): Dosya içeriği
            content_type (str): MIME type
            
        Returns:
            dict: Upload sonucu bilgileri
        """
        try:
            # Dosya hash'i hesapla
            file_hash = hashlib.sha1(file_content).hexdigest()
            
            # B2'ye yükle
            file_info = self.bucket.upload_bytes(
                data_bytes=file_content,
                file_name=file_path,
                content_type=content_type,
                file_infos={
                    'src_last_modified_millis': str(int(os.path.getmtime('app.py') * 1000))  # Example timestamp
                }
            )
            
            result = {
                'success': True,
                'file_id': file_info.id_,
                'file_name': file_info.file_name,
                'download_url': self.get_download_url(file_info.file_name),
                'size': len(file_content),
                'content_type': content_type
            }
            
            logging.info(f"File uploaded to B2: {file_path}")
            return result
            
        except Exception as e:
            logging.error(f"B2 upload failed for {file_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_file(self, file_path):
        """
        B2'den dosya indir
        
        Args:
            file_path (str): B2'deki dosya yolu
            
        Returns:
            bytes: Dosya içeriği veya None
        """
        try:
            # Bucket download_version kullan
            download_version = self.bucket.download_file_by_name(file_path)
            
            # İçeriği bytes olarak oku
            file_content = b''
            for data in download_version.iter_content(chunk_size=8192):
                file_content += data
            
            logging.info(f"File downloaded from B2: {file_path} ({len(file_content)} bytes)")
            return file_content
            
        except Exception as e:
            logging.error(f"B2 download failed for {file_path}: {e}")
            return None
    
    def delete_file(self, file_path):
        """
        B2'den dosya sil
        
        Args:
            file_path (str): B2'deki dosya yolu
            
        Returns:
            bool: Silme başarılı ise True
        """
        try:
            # Dosya bilgisini al
            file_version = self.bucket.get_file_info_by_name(file_path)
            
            # Dosyayı sil
            self.b2_api.delete_file_version(file_version.id_, file_path)
            
            logging.info(f"File deleted from B2: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"B2 delete failed for {file_path}: {e}")
            return False
    
    def get_download_url(self, file_path):
        """
        Dosya için public download URL'i al
        
        Args:
            file_path (str): B2'deki dosya yolu
            
        Returns:
            str: Download URL
        """
        try:
            return self.bucket.get_download_url(file_path)
        except Exception as e:
            logging.error(f"Failed to get download URL for {file_path}: {e}")
            return None
    
    def list_files(self, prefix=""):
        """
        B2'deki dosyaları listele
        
        Args:
            prefix (str): Dosya adı başlangıcı (örn: 'qr_codes/')
            
        Returns:
            list: Dosya listesi
        """
        try:
            files = []
            for file_version, _ in self.bucket.ls(folder_to_list=prefix, recursive=True):
                files.append({
                    'file_name': file_version.file_name,
                    'file_id': file_version.id_,
                    'size': file_version.size,
                    'upload_timestamp': file_version.upload_timestamp
                })
            return files
            
        except Exception as e:
            logging.error(f"B2 list files failed: {e}")
            return []

# Global B2 service instance
b2_service = None

def get_b2_service():
    """B2 service singleton pattern"""
    global b2_service
    if b2_service is None:
        b2_service = B2StorageService()
    return b2_service